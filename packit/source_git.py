# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
packit started as source-git and we're making a source-git module after such a long time, weird
"""

import configparser
import logging
import shutil
import textwrap
from pathlib import Path
from typing import Optional, List, Dict

import git
import yaml
from rebasehelper.exceptions import LookasideCacheError
from rebasehelper.helpers.lookaside_cache_helper import LookasideCacheHelper

from packit.config import Config
from packit.constants import RPM_MACROS_FOR_PREP, DISTRO_DIR, SRC_GIT_CONFIG
from packit.exceptions import PackitException
from packit.patches import PatchMetadata
from packit.pkgtool import PkgTool
from packit.utils import (
    run_command,
    get_default_branch,
)
from packit.specfile import Specfile

logger = logging.getLogger(__name__)


# https://stackoverflow.com/questions/13518819/avoid-references-in-pyyaml
# mypy hated the suggestion from the SA ^, hence an override like this
class SafeDumperWithoutAliases(yaml.SafeDumper):
    def ignore_aliases(self, data):
        # no aliases/anchors in the dumped yaml text
        return True


class SourceGitGenerator:
    """
    Set up a source-git repo in an upstream repo taking downstream patches
    from the corresponding package in Fedora/CentOS/RHEL.

    Attributes:
        config: Packit configuration.
        source_git: Git repository to be initialized as a source-git repo.
        dist_git: Dist-git repository to be used for initialization.
        upstream_ref: Upstream ref which is going to be the starting point of the
            source-git history. This can be a branch, tag or commit sha. It is expected
            that the current HEAD and this ref point to the same commit.
        upstream_url: Git URL to be saved in the source-git configuration. If not specified,
            the fetch URL of the 'origin' remote us used, unless 'upstream_remote' is set.
        upstream_remote: Name of the remote from which the fetch URL is taken as the Git URL
            of the upstream project to be saved in the source-git configuration.
        pkg_tool: Packaging tool to be used to interact with the dist-git repo.
        pkg_name: Name of the package in dist-git.
    """

    def __init__(
        self,
        config: Config,
        source_git: git.Repo,
        dist_git: git.Repo,
        upstream_ref: str,
        upstream_url: Optional[str] = None,
        upstream_remote: Optional[str] = None,
        pkg_tool: Optional[str] = None,
        pkg_name: Optional[str] = None,
    ):
        self.config = config
        self.source_git = source_git
        self.dist_git = dist_git
        self.upstream_ref = upstream_ref
        self.upstream_url = upstream_url or next(
            self.source_git.remote(upstream_remote or "origin").urls
        )
        self.pkg_tool = pkg_tool
        self.pkg_name = pkg_name or Path(self.dist_git.working_dir).name

        self._dist_git_specfile: Optional[Specfile] = None
        self.distro_dir = Path(self.source_git.working_dir, DISTRO_DIR)
        self._dist_git: Optional[git.Repo] = None
        self._patch_comments: dict = {}

    @property
    def dist_git_specfile(self) -> Specfile:
        if not self._dist_git_specfile:
            path = str(Path(self.dist_git.working_dir, f"{self.pkg_name}.spec"))
            self._dist_git_specfile = Specfile(
                path, sources_dir=self.dist_git.working_dir
            )
        return self._dist_git_specfile

    def _run_prep(self):
        """
        run `rpmbuild -bp` in the dist-git repo to get a git-repo
        in the %prep phase so we can pick the commits in the source-git repo
        """
        _packitpatch_path = shutil.which("_packitpatch")
        if not _packitpatch_path:
            raise PackitException(
                "We are trying to unpack a dist-git archive and lay patches on top "
                'by running `rpmbuild -bp` but we cannot find "_packitpatch" command on PATH: '
                "please install packit as an RPM."
            )
        logger.info(f"expanding %prep section in {self.dist_git.working_dir}")

        rpmbuild_args = [
            "rpmbuild",
            "--nodeps",
            "--define",
            f"_topdir {str(self.dist_git.working_dir)}",
            "-bp",
            "--define",
            f"_specdir {str(self.dist_git.working_dir)}",
            "--define",
            f"_sourcedir {str(self.dist_git.working_dir)}",
        ]
        rpmbuild_args += RPM_MACROS_FOR_PREP
        if logger.level <= logging.DEBUG:  # -vv can be super-duper verbose
            rpmbuild_args.append("-v")
        rpmbuild_args.append(self.dist_git_specfile.path)

        run_command(
            rpmbuild_args,
            cwd=self.dist_git.working_dir,
            print_live=True,
        )

    def _get_lookaside_sources(self) -> List[Dict[str, str]]:
        """
        Read "sources" file from the dist-git repo and return a list of dicts
        with path and url to sources stored in the lookaside cache
        """
        pkg_tool = self.pkg_tool or self.config.pkg_tool
        try:
            config = LookasideCacheHelper._read_config(pkg_tool)
            base_url = config["lookaside"]
        except (configparser.Error, KeyError) as e:
            raise LookasideCacheError("Failed to read rpkg configuration") from e

        package = self.pkg_name
        basepath = self.dist_git.working_dir

        sources = []
        for source in LookasideCacheHelper._read_sources(basepath):
            url = "{0}/rpms/{1}/{2}/{3}/{4}/{2}".format(
                base_url,
                package,
                source["filename"],
                source["hashtype"],
                source["hash"],
            )

            path = source["filename"]
            sources.append({"path": path, "url": url})

        return sources

    def get_BUILD_dir(self):
        path = Path(self.dist_git.working_dir)
        build_dirs = [d for d in (path / "BUILD").iterdir() if d.is_dir()]
        if len(build_dirs) > 1:
            raise RuntimeError(f"More than one directory found in {path / 'BUILD'}")
        if len(build_dirs) < 1:
            raise RuntimeError(f"No subdirectory found in {path / 'BUILD'}")
        return build_dirs[0]

    def _rebase_patches(self, patch_comments: Dict[str, List[str]]):
        """Rebase current branch against the from_branch

        Args:
            patch_comments: dict to map patch names to comment lines serving
                as a description of those patches.
        """
        to_branch = "dist-git-commits"  # temporary branch to store the dist-git history
        BUILD_dir = self.get_BUILD_dir()
        prep_repo = git.Repo(BUILD_dir)
        from_branch = get_default_branch(prep_repo)
        logger.info(f"Rebase patches from dist-git {from_branch}.")
        self.source_git.git.fetch(BUILD_dir, f"+{from_branch}:{to_branch}")

        # transform into {patch_name: patch_id}
        patch_ids = {
            p.get_patch_name(): p.index
            for p in self.dist_git_specfile.patches.get("applied", [])
        }

        # -2 - drop first commit which represents tarball unpacking
        # -1 - reverse order, HEAD is last in the sequence
        patch_commits = list(prep_repo.iter_commits(from_branch))[-2::-1]

        for commit in patch_commits:
            self.source_git.git.cherry_pick(
                commit.hexsha,
                keep_redundant_commits=True,
                allow_empty=True,
                strategy_option="theirs",
            )

            # Annotate commits in the source-git repo with patch_id. This info is not provided
            # during the rpm patching process so we need to do it here.
            metadata = PatchMetadata.from_git_trailers(commit)
            # commit.message already ends with \n
            message = commit.message
            message += f"Patch-id: {patch_ids[metadata.name]}\n"
            if patch_comments.get(metadata.name):
                message += "Patch-status: |\n"
            for line in patch_comments.get(metadata.name, []):
                message += f"    # {line}\n"
            self.source_git.git.commit(message=message, amend=True, allow_empty=True)

        self.source_git.git.branch("-D", to_branch)

    def _populate_distro_dir(self):
        """Copy files used in the distro to package and test the software to .distro.

        Raises:
            PackitException, if the dist-git repository is not pristine, that is,
            there are changed or untracked files in it.
        """
        dist_git_is_pristine = (
            not self.dist_git.git.diff() and not self.dist_git.git.clean("-xdn")
        )
        if not dist_git_is_pristine:
            raise PackitException(
                "Cannot initialize a source-git repo. "
                "The corresponding dist-git repository at "
                f"{self.dist_git.working_dir!r} is not pristine."
                "Use 'git reset --hard HEAD' to reset changed files and "
                "'git clean -xdff' to delete untracked files and directories."
            )

        command = ["rsync", "--archive", "--delete"]
        for exclude in ["*.patch", "sources", ".git*"]:
            command += ["--filter", f"exclude {exclude}"]

        command += [
            str(self.dist_git.working_dir) + "/",
            str(self.distro_dir),
        ]

        self.distro_dir.mkdir(parents=True)
        run_command(command)

    def _reset_gitignore(self):
        reset_rules = textwrap.dedent(
            """\
            # Reset gitignore rules
            !*
            """
        )
        Path(self.distro_dir, ".gitignore").write_text(reset_rules)

    def _configure_syncing(self):
        """Populate source-git.yaml"""
        package_config = {}
        package_config.update(
            {
                "upstream_project_url": self.upstream_url,
                "upstream_ref": self.upstream_ref,
                "downstream_package_name": self.pkg_name,
                "specfile_path": f"{DISTRO_DIR}/{self.pkg_name}.spec",
                "patch_generation_ignore_paths": [DISTRO_DIR],
                "patch_generation_patch_id_digits": self.dist_git_specfile.patch_id_digits,
                "sync_changelog": True,
                "synced_files": [
                    {
                        # The trailing-slash is important, as we want to
                        # sync the content of the directory, not the directory
                        # as a whole.
                        "src": f"{DISTRO_DIR}/",
                        "dest": ".",
                        "delete": True,
                        "filters": [
                            "protect .git*",
                            "protect sources",
                            f"exclude {SRC_GIT_CONFIG}",
                            "exclude .gitignore",
                        ],
                    }
                ],
            }
        )
        lookaside_sources = self._get_lookaside_sources()
        if lookaside_sources:
            package_config["sources"] = lookaside_sources

        Path(self.distro_dir, SRC_GIT_CONFIG).write_text(
            yaml.dump(
                package_config,
                Dumper=SafeDumperWithoutAliases,
                default_flow_style=False,
                sort_keys=False,
            )
        )

    def create_from_upstream(self):
        """Create a source-git repo, by transforming downstream patches
        in Git commits applied on top of the selected upstream ref.
        """
        upstream_ref_sha = self.source_git.git.rev_list("-1", self.upstream_ref)
        if upstream_ref_sha != self.source_git.head.commit.hexsha:
            raise PackitException(
                f"{self.upstream_ref!r} is not pointing to the current HEAD "
                f"in {self.source_git.working_dir!r}."
            )
        if not self.dist_git_specfile.uses_autosetup:
            raise PackitException(
                "Initializing source-git repos for packages "
                "not using %autosetup is not supported."
            )

        self._populate_distro_dir()
        self._reset_gitignore()
        self._configure_syncing()

        spec = Specfile(
            f"{self.distro_dir}/{self.pkg_name}.spec",
            sources_dir=self.dist_git.working_dir,
        )
        patch_comments = spec.read_patch_comments()
        spec.remove_patches()

        self.source_git.git.stage(DISTRO_DIR, force=True)
        self.source_git.git.commit(message="Initialize as a source-git repository")

        pkg_tool = PkgTool(
            fas_username=self.config.fas_user,
            directory=self.dist_git.working_dir,
            tool=self.pkg_tool or self.config.pkg_tool,
        )
        pkg_tool.sources()
        self._run_prep()
        self._rebase_patches(patch_comments)
