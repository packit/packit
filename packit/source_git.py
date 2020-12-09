# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
"""
packit started as source-git and we're making a source-git module after such a long time, weird
"""
import logging
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from git import GitCommandError

from packit.config.common_package_config import CommonPackageConfig
from packit.config.config import Config
from packit.config.package_config import PackageConfig
from packit.constants import RPM_MACROS_FOR_PREP
from packit.distgit import DistGit
from packit.exceptions import PackitException
from packit.local_project import LocalProject
from packit.utils.commands import run_command
from packit.utils.repo import clone_centos_package

logger = logging.getLogger(__name__)


class CentOSDistGit(DistGit):
    """ Fedora and CentOS dist-git differ """

    # we store downstream content in source-git in this subdir
    source_git_downstream_suffix = "SPECS"

    @classmethod
    def clone(
        cls,
        config: Config,
        package_config: CommonPackageConfig,
        path: Path,
        branch,
    ) -> "CentOSDistGit":
        clone_centos_package(
            package_config.downstream_package_name, path, branch=branch
        )
        lp = LocalProject(working_dir=path)
        i = cls(config, package_config, local_project=lp)
        return i

    @property
    def absolute_source_dir(self):
        return self.local_project.working_dir / "SOURCES"


def get_distgit_kls_from_repo(
    repo_path: Path, config: Config
) -> Tuple[DistGit, Optional[str], Optional[str]]:
    """
    :return: DistGit instance, centos package name, fedora package name
    """
    path = Path(repo_path)
    pc = PackageConfig(downstream_package_name=path.name)
    lp = LocalProject(working_dir=path)
    if "fedoraproject.org" in lp.git_url:
        return DistGit(config, pc, local_project=lp), None, path.name
    elif "centos.org" in lp.git_url:
        return CentOSDistGit(config, pc, local_project=lp), path.name, None
    raise PackitException(
        f"Dist-git URL {lp.git_url} not recognized, we expected centos.org or fedoraproject.org"
    )


def get_tarball_comment(tarball_path: str) -> Optional[str]:
    """Return the comment header for the tarball

    If written by git-archive, this contains the Git commit ID.
    Return None if the file is invalid or does not contain a comment.

    shamelessly stolen:
    https://pagure.io/glibc-maintainer-scripts/blob/master/f/glibc-sync-upstream.py#_75
    """
    try:
        with tarfile.open(tarball_path) as tar:
            return tar.pax_headers["comment"]
    except Exception as ex:
        logger.debug(f"Could not get 'comment' header from the tarball: {ex}")
        return None


class SourceGitGenerator:
    """
    generate a source-git repo from provided upstream repo
    and a corresponding package in Fedora/CentOS ecosystem
    """

    def __init__(
        self,
        local_project: LocalProject,
        config: Config,
        upstream_url: Optional[str] = None,
        upstream_ref: Optional[str] = None,
        dist_git_path: Optional[Path] = None,
        dist_git_branch: Optional[str] = None,
        fedora_package: Optional[str] = None,
        centos_package: Optional[str] = None,
        tmpdir: Optional[Path] = None,
    ):
        """
        :param local_project: this source-git repo
        :param config: global configuration
        :param upstream_url: upstream repo URL we want to use as a base
        :param upstream_ref: upstream git-ref to use as a base
        :param dist_git_path: path to a local clone of a dist-git repo
        :param dist_git_branch: branch in dist-git to use
        :param fedora_package: pick up specfile and downstream sources from this fedora package
        :param centos_package: pick up specfile and downstream sources from this centos package
        :param tmpdir: path to a directory where temporary repos (upstream,
                       dist-git) will be cloned
        """
        self.local_project = local_project
        self.config = config
        self.tmpdir = tmpdir or Path(tempfile.mkdtemp(prefix="packit-sg-"))
        self._dist_git: Optional[DistGit] = None
        self._primary_archive: Optional[Path] = None
        self._upstream_ref: Optional[str] = upstream_ref
        self.dist_git_branch = dist_git_branch

        if dist_git_path:
            (
                self._dist_git,
                self.centos_package,
                self.fedora_package,
            ) = get_distgit_kls_from_repo(dist_git_path, config)
            self.dist_git_path = dist_git_path
            self.package_config = self.dist_git.package_config
        else:
            self.centos_package = centos_package
            self.fedora_package = fedora_package
            if centos_package:
                self.package_config = PackageConfig(
                    downstream_package_name=centos_package
                )
            else:
                self.fedora_package = (
                    self.fedora_package or local_project.working_dir.name
                )
                self.package_config = PackageConfig(
                    downstream_package_name=fedora_package
                )
            self.dist_git_path = self.tmpdir.joinpath(
                self.package_config.downstream_package_name
            )

        if upstream_url:
            if Path(upstream_url).is_dir():
                self.upstream_repo_path: Path = Path(upstream_url)
                self.upstream_lp: LocalProject = LocalProject(
                    working_dir=self.upstream_repo_path
                )
            else:
                self.upstream_repo_path = self.tmpdir.joinpath(
                    f"{self.package_config.downstream_package_name}-upstream"
                )
                self.upstream_lp = LocalProject(
                    git_url=upstream_url, working_dir=self.upstream_repo_path
                )
        else:
            # $CWD is the upstream repo and we just need to pick
            # downstream stuff
            self.upstream_repo_path = self.local_project.working_dir
            self.upstream_lp = self.local_project

    @property
    def primary_archive(self) -> Path:
        if not self._primary_archive:
            self._primary_archive = self.dist_git.download_upstream_archive()
        return self._primary_archive

    @property
    def dist_git(self) -> DistGit:
        if not self._dist_git:
            self._dist_git = self._get_dist_git()
        return self._dist_git

    @property
    def upstream_ref(self) -> str:
        if self._upstream_ref is None:
            self._upstream_ref = get_tarball_comment(str(self.primary_archive))
            if self._upstream_ref:
                logger.info(
                    "upstream base ref was not set, "
                    f"discovered it from the archive: {self._upstream_ref}"
                )
            else:
                # fallback to HEAD
                try:
                    self._upstream_ref = self.local_project.commit_hexsha
                except ValueError as ex:
                    raise PackitException(
                        "Current branch seems to be empty - we cannot get the hash of "
                        "the top commit. We need to set upstream_ref in packit.yaml to "
                        "distinct between upstream and downstream changes. "
                        "Please set --upstream-ref or pull the upstream git history yourself. "
                        f"Error: {ex}"
                    )
                logger.info(
                    "upstream base ref was not set, "
                    f"falling back to the HEAD commit: {self._upstream_ref}"
                )
        return self._upstream_ref

    @property
    def specfile_path(self) -> Path:
        return self.dist_git.get_root_downstream_dir_for_source_git(
            self.local_project.working_dir
        ).joinpath(self.dist_git.absolute_specfile_path.name)

    def _get_dist_git(
        self,
    ) -> DistGit:
        """
        For given package names, clone the dist-git repo in the given directory
        and return the DistGit class

        :return: DistGit instance (CentOSDistGit if centos_package is set)
        """
        if self.centos_package:
            self.dist_git_branch = self.dist_git_branch or "c8s"
            return CentOSDistGit.clone(
                self.config,
                self.package_config,
                self.dist_git_path,
                branch=self.dist_git_branch,
            )

        self.dist_git_branch = self.dist_git_branch or "master"
        return DistGit.clone(
            self.config,
            self.package_config,
            self.dist_git_path,
            branch=self.dist_git_branch,
        )

    def _pull_upstream_ref(self):
        """
        Pull the base ref from upstream to our source-git repo
        """
        # fetch operation is pretty intense
        # if upstream_ref is a commit, we need to fetch everything
        # if it's a tag or branch, we can only fetch that ref
        self.local_project.fetch(
            str(self.upstream_lp.working_dir), "+refs/heads/*:refs/remotes/origin/*"
        )
        self.local_project.fetch(
            str(self.upstream_lp.working_dir),
            "+refs/remotes/origin/*:refs/remotes/origin/*",
        )
        try:
            next(self.local_project.get_commits())
        except GitCommandError as ex:
            logger.debug(f"Can't get next commit: {ex}")
            # the repo is empty, rebase would fail
            self.local_project.reset(self.upstream_ref)
        else:
            self.local_project.rebase(self.upstream_ref)

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
        logger.info(
            f"expanding %prep section in {self.dist_git.local_project.working_dir}"
        )

        rpmbuild_args = [
            "rpmbuild",
            "--nodeps",
            "--define",
            f"_topdir {str(self.dist_git.local_project.working_dir)}",
            "-bp",
            "--define",
            f"_specdir {str(self.dist_git.absolute_specfile_dir)}",
            "--define",
            f"_sourcedir {str(self.dist_git.absolute_source_dir)}",
        ]
        rpmbuild_args += RPM_MACROS_FOR_PREP
        if logger.level <= logging.DEBUG:  # -vv can be super-duper verbose
            rpmbuild_args.append("-v")
        rpmbuild_args.append(str(self.dist_git.absolute_specfile_path))

        run_command(
            rpmbuild_args,
            cwd=self.dist_git.local_project.working_dir,
            print_live=True,
        )

    def _put_downstream_sources(self):
        """
        place sources from the downstream into the source-git repository
        """
        if self.dist_git_branch:
            self.dist_git.checkout_branch(self.dist_git_branch)
        root_downstream_dir = self.dist_git.get_root_downstream_dir_for_source_git(
            self.local_project.working_dir
        )
        os.makedirs(root_downstream_dir, exist_ok=True)

        shutil.copy2(self.dist_git.absolute_specfile_path, root_downstream_dir)

        logger.info(
            f"Copy all sources from {self.dist_git.absolute_source_dir} to {root_downstream_dir}."
        )

        # we may not want to copy the primary archive - it's worth a debate
        for source in self.dist_git.specfile.get_sources():
            source_dest = root_downstream_dir / Path(source).name
            logger.debug(f"copying {source} to {source_dest}")
            shutil.copy2(source, source_dest)

        self.local_project.stage(self.dist_git.source_git_downstream_suffix)
        self.local_project.commit(message="add downstream distribution sources")

    def _add_packit_config(self):
        packit_yaml_path = self.local_project.working_dir.joinpath(".packit.yaml")
        packit_yaml_path.write_text(
            "---\n"
            f'specfile_path: "{self.specfile_path.relative_to(self.local_project.working_dir)}"\n'
            f'upstream_ref: "{self.upstream_ref}"\n'
            f'patch_generation_ignore_paths: ["{self.dist_git.source_git_downstream_suffix}"]\n\n'
        )
        self.local_project.stage(".packit.yaml")
        self.local_project.commit("add packit.yaml")

    def get_BUILD_dir(self):
        path = self.dist_git.local_project.working_dir
        build_dirs = [d for d in (path / "BUILD").iterdir() if d.is_dir()]
        if len(build_dirs) > 1:
            raise RuntimeError(f"More than one directory found in {path / 'BUILD'}")
        if len(build_dirs) < 1:
            raise RuntimeError(f"No subdirectory found in {path / 'BUILD'}")
        return build_dirs[0]

    def _rebase_patches(self, from_branch):
        """Rebase current branch against the from_branch """
        to_branch = "dist-git-commits"  # temporary branch to store the dist-git history
        logger.info(f"Rebase patches from dist-git {from_branch}.")
        BUILD_dir = self.get_BUILD_dir()
        self.local_project.fetch(BUILD_dir, f"+{from_branch}:{to_branch}")

        # shorter format for better readability in case of an error
        commits_to_cherry_pick = [
            c.hexsha[:8]
            for c in LocalProject(working_dir=BUILD_dir).get_commits(from_branch)
        ][-2::-1]
        if commits_to_cherry_pick:
            self.local_project.git_repo.git.cherry_pick(
                *commits_to_cherry_pick,
                keep_redundant_commits=True,
                allow_empty=True,
                strategy_option="theirs",
            )
        self.local_project.git_repo.git.branch("-D", to_branch)

    def create_from_upstream(self):
        """
        create a source-git repo from upstream
        """
        self._pull_upstream_ref()
        self._put_downstream_sources()
        self._add_packit_config()
        if self.dist_git.specfile.patches:
            self._run_prep()
            self._rebase_patches("master")
            # TODO: patches which are defined but not applied should be copied
