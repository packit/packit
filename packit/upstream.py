# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import datetime
import logging
import os
import re
import shutil
import tarfile
from pathlib import Path
from typing import Optional, List, Tuple, Union

import git
from packaging import version

from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.config import Config
from packit.config.common_package_config import CommonPackageConfig
from packit.constants import DEFAULT_ARCHIVE_EXT, DATETIME_FORMAT
from packit.exceptions import (
    PackitException,
    PackitSRPMNotFoundException,
    PackitFailedToCreateSRPMException,
    PackitCommandFailedError,
    PackitFailedToCreateRPMException,
    PackitRPMNotFoundException,
)
from packit.local_project import LocalProject
from packit.patches import PatchGenerator, PatchMetadata
from packit.specfile import Specfile
from packit.utils import commands, sanitize_branch_name_for_rpm
from packit.utils.commands import run_command
from packit.utils.repo import git_remote_url_to_https_url, get_current_version_command

logger = logging.getLogger(__name__)


class Upstream(PackitRepositoryBase):
    """ interact with upstream project """

    def __init__(
        self,
        config: Config,
        package_config: CommonPackageConfig,
        local_project: LocalProject,
    ):
        """
        :param config: global configuration
        :param package_config: configuration of the upstream project
        :param local_project: public offender
        """
        self._local_project = local_project
        super().__init__(config=config, package_config=package_config)
        self.config = config
        self.package_config = package_config

    def __repr__(self):
        return (
            "Upstream("
            f"config='{self.config}', "
            f"package_config='{self.package_config}', "
            f"local_project='{self.local_project}', "
            f"active_branch='{self.active_branch}')"
        )

    @property
    def local_project(self):
        if not self._local_project:
            self._local_project = LocalProject(
                git_url=self.package_config.upstream_project_url,
                repo_name=self.package_config.upstream_package_name,
            )
        if self._local_project.git_project is None:
            if not self.package_config.upstream_project_url:
                self.package_config.upstream_project_url = git_remote_url_to_https_url(
                    self._local_project.git_url
                )

            self._local_project.git_project = self.config.get_project(
                url=self.package_config.upstream_project_url
            )
            # self._local_project.refresh_the_arguments()
        return self._local_project

    @property
    def active_branch(self) -> str:
        return self.local_project.ref

    def push_to_fork(
        self,
        branch_name: str,
        force: bool = False,
        fork: bool = True,
        remote_name: str = None,
    ) -> Tuple[str, Optional[str]]:
        """
        push current branch to fork if fork=True, else to origin

        :param branch_name: the branch where we push
        :param force: push forcefully?
        :param fork: push to fork?
        :param remote_name: name of remote where we should push
               if None, try to find a ssh_url
        :return: name of the branch where we pushed
        """
        logger.debug(
            f"About to {'force ' if force else ''}push changes to branch {branch_name!r}."
        )
        fork_username = None

        if not remote_name:
            if fork:
                if self.local_project.git_project.is_fork:
                    project = self.local_project.git_project
                else:
                    # ogr is awesome! if you want to fork your own repo, you'll get it!
                    project = self.local_project.git_project.get_fork(create=True)
                fork_username = project.namespace
                fork_urls = project.get_git_urls()

                ssh_url = fork_urls["ssh"]

                remote_name = "fork-ssh"
                for remote in self.local_project.git_repo.remotes:
                    pushurl = next(remote.urls)  # afaik this is what git does as well
                    if ssh_url.startswith(pushurl):
                        logger.info(
                            f"Will use remote {remote!r} using URL {pushurl!r}."
                        )
                        remote_name = str(remote)
                        break
                else:
                    logger.info(f"Creating remote fork-ssh with URL {ssh_url!r}.")
                    self.local_project.git_repo.create_remote(
                        name="fork-ssh", url=ssh_url
                    )
            else:
                # push to origin and hope for the best
                remote_name = "origin"
        logger.info(f"Pushing to remote {remote_name!r} using branch {branch_name!r}.")
        try:
            self.push(refspec=branch_name, force=force, remote_name=remote_name)
        except git.GitError as ex:
            msg = (
                f"Unable to push to remote {remote_name!r} using branch {branch_name!r}, "
                f"the error is:\n{ex}"
            )
            raise PackitException(msg)
        return str(branch_name), fork_username

    def create_pull(
        self,
        pr_title: str,
        pr_description: str,
        source_branch: str,
        target_branch: str,
        fork_username: str = None,
    ) -> None:
        """
        Create upstream pull request using the requested branches
        """
        project = self.local_project.git_project

        try:
            upstream_pr = project.create_pr(
                title=pr_title,
                body=pr_description,
                source_branch=source_branch,
                target_branch=target_branch,
                fork_username=fork_username,
            )
        except Exception as ex:
            logger.error(f"There was an error while creating a PR: {ex!r}")
            raise
        else:
            logger.info(f"PR created: {upstream_pr.url}")

    def create_patches(
        self, upstream: str = None, destination: str = None
    ) -> List[PatchMetadata]:
        """
        Create patches from downstream commits.

        :param destination: str
        :param upstream: str -- git branch or tag
        :return: [PatchMetadata, ...] list of patches
        """
        upstream = upstream or self.get_specfile_version()
        destination = destination or self.local_project.working_dir

        sync_files_to_ignore = [
            str(sf.src.relative_to(self.local_project.working_dir))
            for sf in self.package_config.get_all_files_to_sync().get_raw_files_to_sync(
                self.local_project.working_dir,
                Path(
                    # dest (downstream) is not important, we only care about src (upstream)
                    destination
                ),
            )
        ]
        files_to_ignore = (
            self.package_config.patch_generation_ignore_paths + sync_files_to_ignore
        )

        pg = PatchGenerator(self.local_project)
        return pg.create_patches(upstream, destination, files_to_ignore=files_to_ignore)

    def get_latest_released_version(self) -> str:
        """
        Return version of the upstream project for the latest official release

        :return: the version string (e.g. "1.0.0")
        """

        version = Specfile.get_upstream_version(
            versioneer=None,
            package_name=self.package_config.downstream_package_name,
            category=None,
        )
        logger.info(f"Version in upstream registries is {version!r}.")
        return version

    def get_specfile_version(self) -> str:
        """ provide version from specfile """
        version = self.specfile.get_version()
        logger.info(f"Version in spec file is {version!r}.")
        return version

    def get_version(self) -> str:
        """
        Return version of the latest release available: prioritize bigger from upstream
        package repositories or the version in spec
        """
        ups_ver = self.get_latest_released_version() or ""
        spec_ver = self.get_specfile_version()

        if version.parse(ups_ver) > version.parse(spec_ver):
            logger.warning(f"Version {spec_ver!r} in spec file is outdated.")
            logger.info(f"Picking version {ups_ver!r} from upstream registry.")
            return ups_ver

        logger.info(f"Picking version {spec_ver!r} found in spec file.")
        return spec_ver

    def get_current_version(self) -> str:
        """
        Get version of the project in current state. Tries following steps:

        1. get output from actions
        2. use configured `current_version_command (.packit.yaml)
        3. extract version from `self.get_last_tag()` using `self.get_version_from_tag()`

        :return: version (e.g. 0.1.1)
        """

        action_output = self.get_output_from_action(
            action=ActionName.get_current_version
        )
        if action_output:
            return action_output[-1].strip()

        elif self.package_config.current_version_command:
            ver = self.command_handler.run_command(
                self.package_config.current_version_command,
                return_output=True,
                cwd=self.local_project.working_dir,
            ).strip()
            logger.debug(f"Raw version: {ver}")
        else:
            ver = self.get_version_from_tag(self.get_last_tag())
        logger.debug(f"Version: {ver}")

        ver = sanitize_branch_name_for_rpm(ver)
        logger.debug(f"Sanitized version: {ver}")

        return ver

    def create_archive(self, version: str = None) -> str:
        """
        Create archive, using `git archive` by default, from the content of the upstream
        repository, only committed changes are present in the archive.
        """
        version = version or self.get_current_version()

        package_name = (
            self.package_config.upstream_package_name
            or self.package_config.downstream_package_name
        )
        dir_name = f"{package_name}-{version}"
        logger.debug(f"Name + version = {dir_name}")

        env = {
            "PACKIT_PROJECT_VERSION": version,
            "PACKIT_PROJECT_NAME_VERSION": dir_name,
        }
        if self.has_action(action=ActionName.create_archive):
            outputs = self.get_output_from_action(
                action=ActionName.create_archive, env=env
            )
            if not outputs:
                raise PackitException("No output from create-archive action.")

            archive_path = self._get_archive_path_from_output(outputs)
            if not archive_path:
                raise PackitException(
                    "The create-archive action did not output a path to the generated archive. "
                    "Please make sure that you have valid path in the single line of the output."
                )
            self._add_link_to_archive_from_specdir_if_needed(archive_path)
            return archive_path.name

        return self._create_archive_using_default_way(dir_name, env, version)

    def _create_archive_using_default_way(self, dir_name, env, version) -> str:
        """
        Create an archive using git archive or the configured command.
        Archive will be places in the specfile_directory.

        :return: name of the archive
        """
        archive_name = f"{dir_name}{DEFAULT_ARCHIVE_EXT}"
        relative_archive_path = (self.absolute_specfile_dir / archive_name).relative_to(
            self.local_project.working_dir
        )
        if self.package_config.create_tarball_command:
            archive_cmd = self.package_config.create_tarball_command
        else:
            archive_cmd = [
                "git",
                "archive",
                "--output",
                str(relative_archive_path),
                "--prefix",
                f"{dir_name}/",
                "HEAD",
            ]
        self.command_handler.run_command(archive_cmd, return_output=True, env=env)
        return archive_name

    def _add_link_to_archive_from_specdir_if_needed(self, archive_path: Path) -> None:
        """
        Create a relative symlink to the archive from in the specfile directory.

        :param archive_path: relative path to the archive from the specfile dir
        """
        if archive_path.parent.absolute() != self.absolute_specfile_dir:
            archive_in_spec_dir = self.absolute_specfile_dir / archive_path.name
            relative_archive_path = archive_path.relative_to(self.absolute_specfile_dir)

            logger.info(
                "Linking to the specfile directory:"
                f" {archive_in_spec_dir} -> {relative_archive_path}"
                f" (given path to archive: {archive_path})"
            )
            archive_in_spec_dir.symlink_to(relative_archive_path)

    def _get_archive_path_from_output(self, outputs: List[str]) -> Optional[Path]:
        """
        Parse the archive name from the output in the reverse order.
        - Check if the line is a path and if it exists.

        :param outputs: given output of the custom command
        :return: Path to the archive if we found any.
        """
        for output in reversed(outputs):
            for archive_name in reversed(output.splitlines()):
                try:
                    archive_path = Path(archive_name.strip())

                    if not archive_path.is_absolute():
                        archive_path = self._local_project.working_dir / archive_path

                    if archive_path.is_file():
                        archive_path_absolute = archive_path.absolute()
                        logger.info("Created archive:")
                        logger.info(f"\tparsed   path: {archive_path}")
                        logger.info(f"\tabsolute path: {archive_path_absolute}")
                        return archive_path_absolute
                except OSError as ex:
                    # File too long
                    if ex.errno == 36:
                        logger.error(
                            "Skipping long output command output while getting archive name."
                        )
                        continue
                    raise ex
        return None

    def get_last_tag(self, before: str = None) -> Optional[str]:
        """
        Get last git-tag from the repo.
        :param before: get last tag before the given tag
        """

        logger.debug(
            f"We're about to `git-describe` the upstream repository "
            f"{self.local_project.working_dir}."
        )

        try:
            cmd = ["git", "describe", "--tags", "--abbrev=0"]
            if before:
                cmd += [f"{before}^"]
            last_tag = run_command(
                cmd,
                output=True,
                cwd=self.local_project.working_dir,
            ).strip()
        except PackitCommandFailedError as ex:
            logger.debug(f"{ex!r}")
            logger.info("Can't describe this repository, are there any git tags?")
            # no tags in the git repo
            return None
        return last_tag

    def get_commit_messages(self, after: str = None, before: str = "HEAD") -> str:
        """
        :param after: get commit messages after this revision,
        if None, all commit messages before 'before' will be returned
        :param before:  get commit messages before this revision
        :return: commit messages
        """
        # let's print changes b/w the last 2 revisions;
        # ambiguous argument '0.1.0..HEAD': unknown revision or path not in the working tree.
        # Use '--' to separate paths from revisions, like this
        commits_range = f"{after}..{before}" if after else before
        cmd = [
            "git",
            "log",
            "--no-merges",
            "--pretty=format:- %s (%an)",
            commits_range,
            "--",
        ]
        return run_command(cmd, output=True, cwd=self.local_project.working_dir).strip()

    def fix_spec(self, archive: str, version: str, commit: str):
        """
        In order to create a SRPM from current git checkout, we need to have the spec reference
        the tarball and unpack it. This method updates the spec so it's possible.

        :param archive: relative path to the archive: used as Source0
        :param version: version to set in the spec
        :param commit: commit to set in the changelog
        """
        self._fix_spec_source(archive)
        self._fix_spec_prep(archive)

        # we only care about the first number in the release
        # so that we can re-run `packit srpm`
        git_des_command = [
            "git",
            "describe",
            "--tags",
            "--long",
            "--match",
            "*",
        ]
        try:
            git_des_out = run_command(
                git_des_command, output=True, cwd=self.local_project.working_dir
            ).strip()
        except PackitCommandFailedError as ex:
            # probably no tags in the git repo
            logger.info(f"Exception while describing the repository: {ex!r}")
            git_desc_suffix = ""
        else:
            # git adds various info in the output separated by -
            # so let's just drop version and reuse everything else
            g_desc_raw = git_des_out.rsplit("-", 2)[1:]
            # release components are meant to be separated by ".", not "-"
            git_desc_suffix = "." + ".".join(g_desc_raw)
            # the leading dot is put here b/c git_desc_suffix can be empty
            # and we could have two subsequent dots - rpm errors in such a case
        current_branch = self.local_project.ref
        sanitized_current_branch = sanitize_branch_name_for_rpm(current_branch)
        original_release_number = self.specfile.get_release_number().split(".", 1)[0]
        current_time = datetime.datetime.now().strftime(DATETIME_FORMAT)
        release = (
            f"{original_release_number}.{current_time}."
            f"{sanitized_current_branch}{git_desc_suffix}"
        )

        last_tag = self.get_last_tag()
        msg = ""
        if last_tag:
            msg = self.get_commit_messages(after=last_tag)
        if not msg:
            # no describe, no tag - just a boilerplate message w/ commit hash
            # or, there were no changes b/w HEAD and last_tag, which implies last_tag == HEAD
            msg = f"- Development snapshot ({commit})"
        logger.debug(f"Setting Release in spec to {release!r}.")
        # instead of changing version, we change Release field
        # upstream projects should take care of versions
        self.specfile.set_spec_version(
            version=version,
            release=release,
            changelog_entry=msg,
        )

    def _fix_spec_prep(self, archive):
        prep = self.specfile.spec_content.section("%prep")
        if not prep:
            logger.warning("This package doesn't have a %prep section.")
            return

        # stolen from tito, thanks!
        # https://github.com/dgoodwin/tito/blob/master/src/tito/common.py#L695
        regex = re.compile(r"^(\s*%(?:auto)?setup)(.*?)$")
        for idx, line in enumerate(prep):
            m = regex.match(line)
            if m:
                break
        else:
            logger.error(
                "This package is not using %(auto)setup macro in prep, "
                "packit can't work in this environment."
            )
            return

        archive_root_dir = self.get_archive_root_dir(archive)

        new_setup_line = m[1]
        # replace -n with our -n because it's better
        args_match = re.search(r"(.*?)\s+-n\s+\S+(.*)", m[2])
        if args_match:
            new_setup_line += args_match.group(1)
            new_setup_line += args_match.group(2)
        else:
            new_setup_line += m[2]
        new_setup_line += f" -n {archive_root_dir}"
        logger.debug(
            f"New {'%autosetup' if 'autosetup' in new_setup_line else '%setup'}"
            f" line:\n{new_setup_line}"
        )
        prep[idx] = new_setup_line
        self.specfile.spec_content.replace_section("%prep", prep)
        self.specfile.write_spec_content()

    def _fix_spec_source(self, archive):
        response = self.specfile.get_source(self.package_config.spec_source_id)
        if response:
            self.specfile.set_raw_tag_value(
                response.name, archive, section=response.section_index
            )
        else:
            raise PackitException(
                "The spec file doesn't have sources set "
                f"via {self.package_config.spec_source_id} nor Source."
            )

    def create_srpm(
        self, srpm_path: Union[Path, str] = None, srpm_dir: Union[Path, str] = None
    ) -> Path:
        """
        Create SRPM from the actual content of the repo

        :param srpm_path: path to the srpm
        :param srpm_dir: path to the directory where the srpm is meant to be placed
        :return: path to the srpm
        """

        if self.running_in_service():
            srpm_dir = Path(".")
            rpmbuild_dir = self.absolute_specfile_dir.relative_to(
                self.local_project.working_dir
            )
        else:
            srpm_dir = Path(srpm_dir) if srpm_dir else Path.cwd()
            rpmbuild_dir = self.absolute_specfile_dir

        cmd = [
            "rpmbuild",
            "-bs",
            "--define",
            f"_sourcedir {rpmbuild_dir}",
            "--define",
            f"_srcdir {rpmbuild_dir}",
            "--define",
            f"_specdir {rpmbuild_dir}",
            "--define",
            f"_srcrpmdir {srpm_dir}",
            "--define",
            f"_topdir {rpmbuild_dir}",
            # we also need these 3 so that rpmbuild won't create them
            "--define",
            f"_builddir {rpmbuild_dir}",
            "--define",
            f"_rpmdir {rpmbuild_dir}",
            "--define",
            f"_buildrootdir {rpmbuild_dir}",
            self.package_config.specfile_path,
        ]
        escaped_command = " ".join(cmd)
        logger.debug(f"SRPM build command: {escaped_command}")
        present_srpms = set(srpm_dir.glob("*.src.rpm"))
        logger.debug(f"Present SRPMs: {present_srpms}")
        try:
            out = self.command_handler.run_command(cmd, return_output=True).strip()
        except PackitCommandFailedError as ex:
            logger.error(f"The `rpmbuild` command failed: {ex!r}")
            raise PackitFailedToCreateSRPMException(
                f"reason:\n"
                f"{ex}\n"
                f"command:\n"
                f"{escaped_command}\n"
                f"stdout:\n"
                f"{ex.stdout_output}\n"
                f"stderr:\n"
                f"{ex.stderr_output}"
            ) from ex
        except PackitException as ex:
            logger.error(f"The `rpmbuild` command failed: {ex!r}")
            raise PackitFailedToCreateSRPMException(
                f"The `rpmbuild` command failed:\n{ex}"
            ) from ex

        the_srpm = self._get_srpm_from_rpmbuild_output(out)
        if srpm_path:
            shutil.move(the_srpm, srpm_path)
            return Path(srpm_path)
        if self.running_in_service():
            return self.local_project.working_dir / the_srpm
        return Path(the_srpm)

    def _get_srpm_from_rpmbuild_output(self, output: str) -> str:
        """
        Try to find the srpm file in the `rpmbuild -bs` command output.

        :param output: output of the `rpmbuild -bs` command
        :return: the name of the SRPM file
        """
        logger.debug(f"The `rpmbuild` command output: {output}")
        # not doing 'Wrote: (.+)' since people can have different locales; hi Franto!
        reg = r": (.+\.src\.rpm)$"
        try:
            the_srpm = re.findall(reg, output)[0]
        except IndexError:
            raise PackitSRPMNotFoundException(
                "SRPM cannot be found, something is wrong."
            )
        return the_srpm

    def prepare_upstream_for_srpm_creation(self, upstream_ref: str = None):
        """
        1. determine version
        2. create an archive or download upstream and create patches for sourcegit
        3. fix/update the specfile to use the right archive
        4. download the remote sources

        :param upstream_ref: str, needed for the sourcegit mode
        """
        current_git_describe_version = self.get_current_version()
        upstream_ref = self._expand_git_ref(
            upstream_ref or self.package_config.upstream_ref
        )

        if upstream_ref:
            self.prepare_upstream_using_source_git(upstream_ref)
        else:
            created_archive = self.create_archive(version=current_git_describe_version)
            self.fix_specfile_to_use_local_archive(
                archive=created_archive, archive_version=current_git_describe_version
            )

        # https://github.com/packit/packit-service/issues/314
        if Path(self.local_project.working_dir).joinpath("sources").exists():
            logger.warning('The upstream repo contains "sources" file or a directory.')
            logger.warning(
                "We are unable to download remote sources from spec-file "
                "because the file contains links to archives in Fedora downstream."
            )
            logger.warning("Therefore skipping downloading of remote sources.")
        else:
            # > Method that iterates over all sources and downloads ones,
            # > which contain URL instead of just a file.
            self.specfile.download_remote_sources()

    def fix_specfile_to_use_local_archive(self, archive, archive_version) -> None:
        """
        Update specfile to use the archive with the right version.

        :param archive: path to the archive
        :param archive_version: package version of the archive
        """
        current_commit = self.local_project.commit_hexsha
        env = {
            "PACKIT_PROJECT_VERSION": archive_version,
            "PACKIT_PROJECT_COMMIT": current_commit,
            "PACKIT_PROJECT_ARCHIVE": archive,
        }
        if self.with_action(action=ActionName.fix_spec, env=env):
            self.fix_spec(
                archive=archive, version=archive_version, commit=current_commit
            )

    def prepare_upstream_using_source_git(self, upstream_ref):
        """
        Fetch the tarball and don't check out the upstream ref.

        :param upstream_ref: the base git ref for the source git
        :return: the source directory where we can build the SRPM
        """
        self.fetch_upstream_archive()
        self.create_patches_and_update_specfile(upstream_ref)
        old_release = self.specfile.get_release_number()
        try:
            old_release_int = int(old_release)
            new_release = str(old_release_int + 1)
        except ValueError:
            new_release = str(old_release)

        current_commit = self.local_project.commit_hexsha
        release_to_update = f"{new_release}.g{current_commit}"
        msg = f"Downstream changes ({current_commit})"
        self.specfile.set_spec_version(
            release=release_to_update, changelog_entry=f"- {msg}"
        )

    def create_patches_and_update_specfile(self, upstream_ref) -> None:
        """
        Create patches for the sourcegit and add them to the specfile.

        :param upstream_ref: the base git ref for the source git
        """
        if self.with_action(action=ActionName.create_patches):
            patches = self.create_patches(
                upstream=upstream_ref, destination=str(self.absolute_specfile_dir)
            )
            self.specfile_add_patches(patches)

    def koji_build(
        self,
        scratch: bool = False,
        nowait: bool = False,
        koji_target: Optional[str] = None,
        srpm_path: Optional[Path] = None,
    ):
        """
        Perform a `koji build` in the repository

        :param scratch: should the build be a scratch build?
        :param nowait: don't wait on build?
        :param koji_target: koji target to pick (see `koji list-targets`)
        :param srpm_path: use selected SRPM for build, not dist-git repo & ref
        """
        if not koji_target:
            raise PackitException(
                "koji target needs to be set when building directly from upstream"
            )
        # we can't use fedpkg b/c upstream repo is not dist-git
        cmd = ["koji", "build"]
        if scratch:
            cmd.append("--scratch")
        if nowait:
            cmd.append("--nowait")
        cmd += [koji_target, str(srpm_path)]
        logger.info("Starting a koji build.")
        if not nowait:
            logger.info(
                "We will be actively waiting for the build to finish, it may take some time."
            )
        return commands.run_command_remote(
            cmd,
            cwd=self.local_project.working_dir,
            output=True,
            decode=True,
            print_live=True,
        )

    def create_rpms(self, rpm_dir: Union[str, Path] = None) -> List[Path]:
        """
        Create RPMs from the actual content of the repo.
        :param rpm_dir: path to the directory where the rpms are meant to be placed
        :return: paths to the RPMs
        """
        rpm_dir = rpm_dir or os.getcwd()
        src_dir = rpmbuild_dir = str(self.absolute_specfile_dir)

        cmd = [
            "rpmbuild",
            "-bb",
            "--define",
            f"_sourcedir {rpmbuild_dir}",
            "--define",
            f"_srcdir {src_dir}",
            "--define",
            f"_specdir {rpmbuild_dir}",
            "--define",
            f"_topdir {rpmbuild_dir}",
            "--define",
            f"_builddir {rpmbuild_dir}",
            "--define",
            f"_rpmdir {rpm_dir}",
            "--define",
            f"_buildrootdir {rpmbuild_dir}",
            self.package_config.specfile_path,
        ]

        escaped_command = " ".join(cmd)
        logger.debug(f"RPM build command: {escaped_command}")
        try:
            out = self.command_handler.run_command(cmd, return_output=True).strip()
        except PackitCommandFailedError as ex:
            logger.error(f"The `rpmbuild` command failed: {ex!r}")
            raise PackitFailedToCreateRPMException(
                f"reason:\n"
                f"{ex}\n"
                f"command:\n"
                f"{escaped_command}\n"
                f"stdout:\n"
                f"{ex.stdout_output}\n"
                f"stderr:\n"
                f"{ex.stderr_output}"
            ) from ex
        except PackitException as ex:
            logger.error(f"The `rpmbuild` command failed: {ex!r}")
            raise PackitFailedToCreateRPMException(
                f"The `rpmbuild` command failed:\n{ex}"
            ) from ex

        rpms = self._get_rpms_from_rpmbuild_output(out)
        return [Path(rpm) for rpm in rpms]

    def _get_rpms_from_rpmbuild_output(self, output: str) -> List[str]:
        """
        Try to find the rpm files in the `rpmbuild -bb` command output.

        :param output: output of the `rpmbuild -bb` command
        :return: the names of the RPM files
        """
        logger.debug(f"The `rpmbuild` command output: {output}")
        reg = r": (.+\.rpm)"
        logger.debug(re.findall(reg, output))
        rpms = re.findall(reg, output)

        if not rpms:
            raise PackitRPMNotFoundException(
                "RPMs cannot be found, something is wrong."
            )

        return rpms

    def _expand_git_ref(self, ref: Optional[str]) -> str:
        """
        Expands given git ref.
        If given globbing pattern, tries to expand it to git ref.
        If no ref given or isn't globbing pattern, returns it.

        :param ref: git ref to be expanded if necessary
        :return: same ref if is not globbing pattern, otherwise expanded
        """
        if not ref or not re.match(r".*[\[\?\*].*", ref):
            # regex matches any globbing pattern (`[`, `?` or `*` is used)
            logger.debug("No ref given or is not glob pattern")
            return ref

        tag = self.command_handler.run_command(
            get_current_version_command(
                ref.lstrip("branches/"),
                refs="all" if ref.startswith("branches/") else "tags",
            ),
            return_output=True,
            cwd=self.local_project.working_dir,
        ).strip()
        logger.debug(f"Matching tag for {ref}: {tag}")

        return tag

    @staticmethod
    def _template2regex(template) -> str:
        """
        Converts tag template to regex with named groups.

        :param template: tag_template string
        :return: regex string which can be used by python re module
        """

        p = re.compile(r"{(.*?)}")
        return p.sub(r"(?P<\g<1>>.*)", template)

    def get_version_from_tag(self, tag: str) -> str:
        """
        Extracts version from git tag using upstream_template_tag

        :param tag: git tag containing version
        :return: version string
        """

        field = "version"
        regex = self._template2regex(self.package_config.upstream_tag_template)
        p = re.compile(regex)
        match = p.match(tag)
        if match and field in match.groupdict():
            return match.group(field)
        else:
            msg = (
                f'Unable to extract "{field}" from {tag} using '
                f"{self.package_config.upstream_tag_template}"
            )
            logger.error(msg)
            raise PackitException(msg)

    def convert_version_to_tag(self, version_: str) -> str:
        """
        Converts version to tag using upstream_tag_tepmlate

        :param version_: version to be converted
        upstream_template_tag
        :return: tag
        """
        try:
            tag = self.package_config.upstream_tag_template.format(version=version_)
        except KeyError:
            msg = (
                f"Invalid upstream_tag_template: {self.package_config.upstream_tag_template} - "
                f'"version" placeholder is missing'
            )
            logger.error(msg)
            raise PackitException(msg)

        return tag

    def get_archive_root_dir(self, archive: str) -> Union[str, None]:
        """
        Returns archive root dir.
        It uses 2 techniques:
        1. tries to extract it directly from archive.
        2. will generate name based on archive_root_dir_template

        Currently supported archives:
        * tar including compression (for details check python tarfile module doc)

        :param archive: name of archive
        :return: archive top level directory or None

        .. raises:: PackitException if failed - all used methods returned None
        """

        archive_root_dir = None

        logger.debug("Trying to extract archive_root_dir from known archives")
        if tarfile.is_tarfile(f"{self.absolute_specfile_dir}/{archive}"):
            logger.debug(f"Archive {archive} is tar.")
            archive_root_dir = self.get_archive_root_dir_from_tar(archive)
        else:
            logger.debug(f"Archive {archive} is not tar.")

        if archive_root_dir is None:
            logger.debug(
                "Using archive_root_dir_template config option. If not set it defaults to "
                "{{upstream_pkg_name}}-{{version}}. Check "
                "https://packit.dev/docs/configuration/#archive_root_dir_template for more details."
            )
            archive_root_dir = self.get_archive_root_dir_from_template()

        return archive_root_dir

    def get_archive_root_dir_from_tar(self, archive: str) -> Union[str, None]:
        """
        Returns tar archive top-level directory, if there is exactly one.

        :param archive: name of tar/compressed tar archive
        :return: archive top level directory if exactly one is found
                None in other cases
        """

        tar = tarfile.open(f"{self.absolute_specfile_dir}/{archive}")
        root_dirs = set()
        for tar_item in tar.getmembers():
            if tar_item.isdir() and "/" not in tar_item.name:
                root_dirs.add(tar_item.name)
            # required for archives where top-level dir was added using tar --transform
            # option - in that case, tar archive will not contain dir related entry
            if tar_item.isfile() and "/" in tar_item.name:
                root_dirs.add(tar_item.name.split("/")[0])

        root_dirs_count = len(root_dirs)
        archive_root_items_count = len(
            {i.name for i in tar.getmembers() if "/" not in i.name}
        )

        if root_dirs_count == 1:
            root_dir = root_dirs.pop()
            logger.debug(f"Directory {root_dir} found in archive {archive}")
            return root_dir
        elif root_dirs_count == 0:
            logger.warning(f"No directory found in archive {archive}.")
        elif root_dirs_count >= 2:
            logger.warning(
                f"Archive {archive} contains multiple directories on the top level: "
                f"the common practice in the industry is to have only one in the "
                f'following format: "PACKAGE-VERSION"'
            )
        elif archive_root_items_count > 1:
            logger.warning(
                f"Archive f{archive} contains multiple root items. It can be "
                f"intentional or can signal incorrect archive structure."
            )
        return None

    def get_archive_root_dir_from_template(self) -> Union[str, None]:
        """
        Generates archive root dir based on archive_root_dir_template.
        archive_root_dir_template default value is "{upstream_pkg_name}-{version}"

        :returns: archive root dir name based on template
        """
        template = self.package_config.archive_root_dir_template
        logger.debug(
            f"archive_root_dir_template is set or defaults to if not set to: {template}"
        )
        archive_root_dir = template.replace(
            "{upstream_pkg_name}", self.package_config.upstream_package_name
        ).replace("{version}", self.get_version())
        not_replaced = re.findall("{.*?}", archive_root_dir)
        if not_replaced:
            logger.warning(
                f"Probably not all archive_root_dir_template tags were "
                f"replaced: {' ,'.join(not_replaced)}"
            )
        return archive_root_dir
