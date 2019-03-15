import logging
import os
from typing import Optional, List, Tuple

import git
from rebasehelper.specfile import SpecFile
from rebasehelper.versioneer import versioneers_runner

from packit.config import Config, PackageConfig
from packit.exceptions import PackitException
from packit.local_project import LocalProject
from packit.utils import run_command

logger = logging.getLogger(__name__)


class Upstream:
    """ interact with upstream project """

    def __init__(self, config: Config, package_config: PackageConfig):
        self.config = config
        self.package_config = package_config

        self._local_project = None
        self._specfile = None

        self.package_name: Optional[str] = self.package_config.downstream_package_name
        self.upstream_project_url: str = self.package_config.upstream_project_url

    @property
    def active_branch(self):
        return self.local_project.ref

    @property
    def specfile_path(self) -> Optional[str]:
        if self.package_name:
            return os.path.join(
                self.local_project.working_dir, f"{self.package_name}.spec"
            )
        return None

    @property
    def local_project(self):
        """ return an instance of LocalProject """
        if self._local_project is None:
            self._local_project = LocalProject(path_or_url=self.upstream_project_url)
        return self._local_project

    @property
    def specfile(self):
        if self._specfile is None:
            self._specfile = SpecFile(
                path=self.specfile_path,
                sources_location=self.local_project.working_dir,
                changelog_entry=None,
            )
        return self._specfile

    def checkout_pr(self, pr_id: int) -> None:
        """
        Checkout the branch for the pr.

        TODO: Move this to ogr and make it compatible with other git forges.
        """
        self.local_project.git_repo.remote().fetch(
            refspec=f"pull/{pr_id}/head:pull/{pr_id}"
        )
        self.local_project.git_repo.refs[f"pull/{pr_id}"].checkout()

    def checkout_release(self, version: str) -> None:
        logger.info("Checking out upstream version %s", version)
        try:
            self.local_project.git_repo.git.checkout(version)
        except Exception as ex:
            raise PackitException(f"Cannot checkout release tag: {ex}.")

    def get_commits_to_upstream(
        self, upstream: str, add_usptream_head_commit=False
    ) -> List[git.Commit]:
        """
        Return the list of different commits between current branch and upstream rev/tag.

        Always choosing the first-parent, so we have a line/path of the commits.
        It contains merge-commits from the master and commits on top of the master.
        (e.g. commits from PR)

        :param add_usptream_head_commit: bool
        :param upstream: str -- git branch or tag
        :return: list of commits (last commit on the current branch.).
        """

        if upstream in self.local_project.git_repo.tags:
            upstream_ref = upstream
        else:
            upstream_ref = f"origin/{upstream}"
            if upstream_ref not in self.local_project.git_repo.refs:
                raise Exception(
                    f"Upstream {upstream_ref} branch nor {upstream} tag not found."
                )

        commits = list(
            self.local_project.git_repo.iter_commits(
                rev=f"{upstream_ref}..{self.local_project.ref}",
                reverse=True,
                first_parent=True,
            )
        )
        if add_usptream_head_commit:
            commits.insert(
                0, self.local_project.git_repo.refs[f"{upstream_ref}"].commit
            )

        logger.debug(
            f"Delta ({upstream_ref}..{self.local_project.ref}): {len(commits)}"
        )
        return commits

    def create_patches(
        self, upstream: str = None, destination: str = None
    ) -> List[Tuple[str, str]]:
        """
        Create patches from downstream commits.

        :param destination: str
        :param upstream: str -- git branch or tag
        :return: [(patch_name, msg)] list of created patches (tuple of the file name and commit msg)
        """

        upstream = upstream or self.get_specfile_version()
        commits = self.get_commits_to_upstream(upstream, add_usptream_head_commit=True)
        patch_list = []

        destination = destination or self.local_project.working_dir

        for i, commit in enumerate(commits[1:]):
            parent = commits[i]

            patch_name = f"{i + 1:04d}-{commit.hexsha}.patch"
            patch_path = os.path.join(destination, patch_name)
            patch_msg = f"{commit.summary}\nAuthor: {commit.author.name} <{commit.author.email}>"

            logger.debug(f"PATCH: {patch_name}\n{patch_msg}")
            diff = run_command(
                cmd=[
                    "git",
                    "diff",
                    "--patch",
                    parent.hexsha,
                    commit.hexsha,
                    "--",
                    ".",
                    '":(exclude)redhat"',
                ],
                cwd=self.local_project.working_dir,
                output=True,
            )

            with open(patch_path, mode="w") as patch_file:
                patch_file.write(diff)
            patch_list.append((patch_name, patch_msg))

        return patch_list

    def get_latest_released_version(self) -> str:
        """
        Return version of the upstream project for the latest official release

        :return: the version string (e.g. "1.0.0")
        """
        version = versioneers_runner.run(
            versioneer=None,
            package_name=self.package_config.downstream_package_name,
            category=None,
        )
        logger.info(f'Version in upstream registries is "f{version}".')
        return version

    def get_specfile_version(self) -> str:
        """ provide version from specfile """
        version = self.specfile.get_full_version()
        logger.info(f'Version in spec file is "f{version}".')
        return version

    def get_version(self) -> str:
        """
        Return version of latest release: prioritize upstream
        package repositories over the version in spec
        """
        ups_ver = self.get_latest_released_version()
        spec_ver = self.get_specfile_version()
        # we're running both so that results of each function are logged and user is aware
        if ups_ver:
            logger.info(
                "Picking version of the latest release from the upstream registry over spec file."
            )
            return ups_ver
        return spec_ver
