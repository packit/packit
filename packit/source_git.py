# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
packit started as source-git and we're making a source-git module after such a long time, weird
"""

import logging
import shutil
import textwrap
from pathlib import Path
from typing import Optional

import git
import yaml
from specfile import Specfile

from packit.config import Config
from packit.constants import (
    RPM_MACROS_FOR_PREP,
    DISTRO_DIR,
    SRC_GIT_CONFIG,
    FROM_DIST_GIT_TOKEN,
    REPO_NOT_PRISTINE_HINT,
)
from packit.exceptions import PackitException
from packit.patches import PatchMetadata
from packit.pkgtool import PkgTool
from packit.utils import (
    commit_message_file,
    run_command,
    get_default_branch,
    get_file_author,
)
from packit.utils.lookaside import get_lookaside_sources
from packit.utils.repo import is_the_repo_pristine

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
            the fetch URL of the 'origin' remote is used, unless 'upstream_remote' is set.
        upstream_remote: Name of the remote from which the fetch URL is taken as the Git URL
            of the upstream project to be saved in the source-git configuration.
        pkg_tool: Packaging tool to be used to interact with the dist-git repo.
        pkg_name: Name of the package in dist-git.
        ignore_missing_autosetup: Do not require %autosetup to be used in
            the %prep section of specfile.
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
        ignore_missing_autosetup: bool = False,
    ):
        self.config = config
        self.source_git = source_git
        self.dist_git = dist_git
        self.upstream_ref = upstream_ref
        try:
            self.upstream_url = upstream_url or next(
                self.source_git.remote(upstream_remote or "origin").urls
            )
        except ValueError as exc:
            logger.debug(f"Failed when getting upstream URL: {exc}")
            raise PackitException(
                "Unable to tell the URL of the upstream repository because there is no remote "
                f"called '{upstream_remote or 'origin'}' in {self.source_git.working_dir}. "
                "Please specify the correct upstream remote using '--upstream-remote' or the "
                "upstream URL, using '--upstream-url'."
            )
        self.pkg_tool = pkg_tool
        self.pkg_name = pkg_name or Path(self.dist_git.working_dir).name
        self.ignore_missing_autosetup = ignore_missing_autosetup

        self._dist_git_specfile: Optional[Specfile] = None
        self.distro_dir = Path(self.source_git.working_dir, DISTRO_DIR)
        self._dist_git: Optional[git.Repo] = None
        self._patch_comments: dict = {}

    @property
    def dist_git_specfile(self) -> Specfile:
        if not self._dist_git_specfile:
            path = str(Path(self.dist_git.working_dir, f"{self.pkg_name}.spec"))
            self._dist_git_specfile = Specfile(
                path, sourcedir=self.dist_git.working_dir, autosave=True
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
            f"_specdir {self.dist_git.working_dir}",
            "--define",
            f"_sourcedir {self.dist_git.working_dir}",
        ]

        rpmbuild_args += RPM_MACROS_FOR_PREP
        if logger.level <= logging.DEBUG:  # -vv can be super-duper verbose
            rpmbuild_args.append("-v")
        rpmbuild_args.append(str(self.dist_git_specfile.path))

        run_command(
            rpmbuild_args,
            cwd=self.dist_git.working_dir,
            print_live=True,
        )

    def get_BUILD_dir(self):
        path = Path(self.dist_git.working_dir)
        build_dirs = [d for d in (path / "BUILD").iterdir() if d.is_dir()]
        if len(build_dirs) > 1:
            raise RuntimeError(f"More than one directory found in {path / 'BUILD'}")
        if not build_dirs:
            raise RuntimeError(f"No subdirectory found in {path / 'BUILD'}")
        return build_dirs[0]

    def _rebase_patches(self):
        """Rebase current branch against the from_branch."""
        to_branch = "dist-git-commits"  # temporary branch to store the dist-git history
        BUILD_dir = self.get_BUILD_dir()
        prep_repo = git.Repo(BUILD_dir)
        from_branch = get_default_branch(prep_repo)
        logger.info(f"Rebase patches from dist-git {from_branch}.")
        self.source_git.git.fetch(BUILD_dir, f"+{from_branch}:{to_branch}")

        # transform into {patch_name: patch_id}
        with self.dist_git_specfile.patches() as patches:
            patch_ids = {p.filename: p.number for p in patches}
            patch_comments = {p.filename: p.comments.raw for p in patches}

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
            trailers = [("Patch-id", patch_ids[metadata.name])]
            patch_status = ""
            for line in patch_comments.get(metadata.name, []):
                patch_status += f"    # {line}\n"
            if patch_status:
                trailers.append(("Patch-status", f"|\n{patch_status}"))
            trailers.append((FROM_DIST_GIT_TOKEN, self.dist_git.head.commit.hexsha))

            author = None
            # If the commit subject matches the one used in _packitpatch
            # when applying patches with 'patch', get the original (first)
            # author of the patch file in dist-git.
            if commit.message.startswith(f"Apply patch {metadata.name}"):
                author = get_file_author(self.dist_git, metadata.name)
            logger.debug(f"author={author}")

            with commit_message_file(
                commit.message, trailers=trailers
            ) as commit_message:
                self.source_git.git.commit(
                    file=commit_message, author=author, amend=True, allow_empty=True
                )

        self.source_git.git.branch("-D", to_branch)

    def _populate_distro_dir(self):
        """Copy files used in the distro to package and test the software to .distro.

        Raises:
            PackitException, if the dist-git repository is not pristine, that is,
            there are changed or untracked files in it.
        """
        if not is_the_repo_pristine(self.dist_git):
            raise PackitException(
                "Cannot initialize a source-git repo. "
                "The corresponding dist-git repository at "
                f"{self.dist_git.working_dir!r} is not pristine. "
                f"{REPO_NOT_PRISTINE_HINT}"
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
        with self.dist_git_specfile.patches() as patches:
            try:
                patch_id_digits = patches[0].number_digits
            except (IndexError, AttributeError):
                patch_id_digits = 1
        package_config = {}
        package_config.update(
            {
                "upstream_project_url": self.upstream_url,
                "upstream_ref": self.upstream_ref,
                "downstream_package_name": self.pkg_name,
                "specfile_path": f"{DISTRO_DIR}/{self.pkg_name}.spec",
                "patch_generation_ignore_paths": [DISTRO_DIR],
                "patch_generation_patch_id_digits": patch_id_digits,
                "sync_changelog": True,
                "files_to_sync": [
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
        lookaside_sources = get_lookaside_sources(
            self.pkg_tool or self.config.pkg_tool,
            self.pkg_name,
            self.dist_git.working_dir,
        )
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
        with self.dist_git_specfile.prep() as prep:
            if "%autosetup" not in prep:
                if not self.ignore_missing_autosetup:
                    raise PackitException(
                        "Initializing source-git repos for packages "
                        "not using %autosetup is not allowed by default. "
                        "You can use --ignore-missing-autosetup option to enforce "
                        "running the command without %autosetup."
                    )
                logger.warning(
                    "Source-git repos for packages not using %autosetup may be not initialized"
                    "properly or may not work with other packit commands."
                )

        self._populate_distro_dir()
        self._reset_gitignore()
        self._configure_syncing()

        spec = Specfile(
            f"{self.distro_dir}/{self.pkg_name}.spec",
            sourcedir=self.dist_git.working_dir,
            autosave=True,
        )
        with spec.patches() as patches:
            patches.clear()

        self.source_git.git.stage(DISTRO_DIR, force=True)
        message = f"""Initialize as a source-git repository

{FROM_DIST_GIT_TOKEN}: {self.dist_git.head.commit.hexsha}
"""
        self.source_git.git.commit(message=message)

        pkg_tool = PkgTool(
            fas_username=self.config.fas_user,
            directory=self.dist_git.working_dir,
            tool=self.pkg_tool or self.config.pkg_tool,
        )
        pkg_tool.sources()
        self._run_prep()
        self._rebase_patches()
