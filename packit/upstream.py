# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

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
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional, List, Tuple

import git
from packaging import version

from packit import utils
from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.config import Config, PackageConfig, SyncFilesConfig
from packit.constants import COMMON_ARCHIVE_EXTENSIONS
from packit.exceptions import (
    PackitException,
    PackitSRPMNotFoundException,
    PackitFailedToCreateSRPMException,
    PackitCommandFailedError,
)
from packit.local_project import LocalProject
from packit.specfile import Specfile
from packit.utils import is_a_git_ref, run_command, git_remote_url_to_https_url

logger = logging.getLogger(__name__)


class Upstream(PackitRepositoryBase):
    """ interact with upstream project """

    def __init__(
        self, config: Config, package_config: PackageConfig, local_project: LocalProject
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

        self.files_to_sync: Optional[SyncFilesConfig] = self.package_config.synced_files

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

    def get_commits_to_upstream(
        self, upstream: str, add_upstream_head_commit=False
    ) -> List[git.Commit]:
        """
        Return the list of different commits between current branch and upstream rev/tag.

        Always choosing the first-parent, so we have a line/path of the commits.
        It contains merge-commits from the master and commits on top of the master.
        (e.g. commits from PR)

        :param add_upstream_head_commit: bool
        :param upstream: str -- git branch or tag
        :return: list of commits (last commit on the current branch.).
        """

        if is_a_git_ref(repo=self.local_project.git_repo, ref=upstream):
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
        if add_upstream_head_commit:
            commits.insert(0, self.local_project.git_repo.commit(upstream_ref))

        logger.debug(
            f"Delta ({upstream_ref}..{self.local_project.ref}): {len(commits)}"
        )
        return commits

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
            f"About to {'force ' if force else ''}push changes to branch {branch_name}."
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
                        logger.info(f"Will use remote {remote} using URL {pushurl}.")
                        remote_name = str(remote)
                        break
                else:
                    logger.info(f"Creating remote fork-ssh with URL {ssh_url}.")
                    self.local_project.git_repo.create_remote(
                        name="fork-ssh", url=ssh_url
                    )
            else:
                # push to origin and hope for the best
                remote_name = "origin"
        logger.info(f"Pushing to remote {remote_name} using branch {branch_name}.")
        try:
            self.push(refspec=branch_name, force=force, remote_name=remote_name)
        except git.GitError as ex:
            msg = (
                f"Unable to push to remote {remote_name} using branch {branch_name}, "
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
            upstream_pr = project.pr_create(
                title=pr_title,
                body=pr_description,
                source_branch=source_branch,
                target_branch=target_branch,
                fork_username=fork_username,
            )
        except Exception as ex:
            logger.error("there was an error while create a PR: %r", ex)
            raise
        else:
            logger.info(f"PR created: {upstream_pr.url}")

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
        commits = self.get_commits_to_upstream(upstream, add_upstream_head_commit=True)

        destination = destination or self.local_project.working_dir

        patches_to_create = []

        sync_files_to_ignore = [
            str(sf.src.relative_to(self.local_project.working_dir))
            for sf in self.package_config.get_all_files_to_sync().get_raw_files_to_sync(
                Path(self.local_project.working_dir),
                Path(
                    # dest (downstream) is not important, we only care about src (upstream)
                    destination
                ),
            )
        ]
        files_to_ignore = (
            self.package_config.patch_generation_ignore_paths + sync_files_to_ignore
        )

        for i, commit in enumerate(commits[1:]):
            parent = commits[i]

            git_diff_cmd = [
                "git",
                "diff",
                "--patch",
                parent.hexsha,
                commit.hexsha,
                "--",
                ".",
            ] + [f":(exclude){file_to_ignore}" for file_to_ignore in files_to_ignore]
            diff = run_command(
                cmd=git_diff_cmd,
                cwd=self.local_project.working_dir,
                output=True,
                decode=False,
            )

            if not diff:
                logger.info(f"No patch for commit: {commit.summary} ({commit.hexsha})")
                continue

            patches_to_create.append((commit, diff))

        patch_list = []
        for i, (commit, diff) in enumerate(patches_to_create):
            patch_name = f"{i + 1:04d}-{commit.hexsha}.patch"
            patch_path = os.path.join(destination, patch_name)
            patch_msg = f"{commit.summary}\nAuthor: {commit.author.name} <{commit.author.email}>"

            logger.debug(f"Saving patch: {patch_name}\n{patch_msg}")
            with open(patch_path, mode="wb") as patch_file:
                patch_file.write(diff)
            patch_list.append((patch_name, patch_msg))

        return patch_list

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
        ups_ver = version.parse(self.get_latest_released_version() or "")
        logger.debug(f"Version in upstream package repositories: {ups_ver}")
        spec_ver = version.parse(self.get_specfile_version())
        logger.debug(f"Version in spec file: {spec_ver}")

        if ups_ver > spec_ver:
            logger.warning("Version in spec file is outdated")
            logger.info(
                "Picking version of the latest release from the upstream registry."
            )
            return str(ups_ver)
        logger.info("Picking version found in spec file.")
        return str(spec_ver)

    def get_current_version(self) -> str:
        """
        Get version of the project in current state (hint `git describe`)

        :return: e.g. 0.1.1.dev86+ga17a559.d20190315 or 0.6.1.1.gce4d84e
        """
        action_output = self.get_output_from_action(
            action=ActionName.get_current_version
        )
        if action_output:
            return action_output[-1].strip()

        ver = self.command_handler.run_command(
            self.package_config.current_version_command, return_output=True
        ).strip()
        logger.debug("version = %s", ver)
        # RPM refuses dashes in version/release
        ver = ver.replace("-", ".")
        logger.debug("sanitized version = %s", ver)
        return ver

    def get_archive_extension(self, archive_basename: str, version: str) -> str:
        """
        Obtains archive extension from SpecFile based on basename of the archive.
        Defaults to .tar.gz if no Source corresponds to the basename.
        """
        for source in self.specfile.get_sources():
            base = os.path.basename(source)
            # Version in archive_basename could contain hash, the version
            # can be different from Spec version. Replace it to ensure proper match.
            base = base.replace(self.specfile.get_version(), version)
            if base.startswith(archive_basename):
                archive_basename_len = len(archive_basename)
                return base[archive_basename_len:]
        return ".tar.gz"

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
        logger.debug("name + version = %s", dir_name)

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
        archive_extension = self.get_archive_extension(dir_name, version)
        if archive_extension not in COMMON_ARCHIVE_EXTENSIONS:
            raise PackitException(
                "The target archive doesn't use a common extension ({}), "
                "git archive can't be used. Please provide your own script "
                "for archive creation.".format(", ".join(COMMON_ARCHIVE_EXTENSIONS))
            )
        archive_name = f"{dir_name}{archive_extension}"
        relative_archive_path = (self.absolute_specfile_dir / archive_name).relative_to(
            self.local_project.working_dir
        )
        if self.package_config.create_tarball_command:
            archive_cmd = self.package_config.create_tarball_command
        else:
            archive_cmd = [
                "git",
                "archive",
                "-o",
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
            logger.info(f"Linking to the specfile directory: {archive_in_spec_dir}")
            archive_in_spec_dir.symlink_to(archive_path)

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
                    archive_path = Path(
                        self._local_project.working_dir, archive_name.strip()
                    )
                    if archive_path.is_file():
                        logger.info(f"Created archive: {archive_path}")
                        return archive_path
                except OSError as ex:
                    # File too long
                    if ex.errno == 36:
                        logger.error(
                            f"Skipping long output command output while getting archive name"
                        )
                        continue
                    raise ex
        return None

    def fix_spec(self, archive: str, version: str, commit: str):
        """
        In order to create a SRPM from current git checkout, we need to have the spec reference
        the tarball and unpack it. This method updates the spec so it's possible.

        :param archive: relative path to the archive: used as Source0
        :param version: version to set in the spec
        :param commit: commit to set in the changelog
        """
        self._fix_spec_source(archive)
        self._fix_spec_prep(version)

        msg = f"Development snapshot ({commit})"
        self.specfile.set_spec_version(version=f"{version}", changelog_entry=msg)

    def _fix_spec_prep(self, version):
        prep = self.specfile.spec_content.section("%prep")
        if not prep:
            logger.warning("this package doesn't have a %prep section")
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
                "this package is not using %(auto)setup macro in prep, "
                "packit can't work in this environment"
            )
            return

        new_setup_line = m[1]
        # replace -n with our -n because it's better
        args_match = re.search(r"(.*?)\s+-n\s+\S+(.*)", m[2])
        if args_match:
            new_setup_line += args_match.group(1)
            new_setup_line += args_match.group(2)
        else:
            new_setup_line += m[2]
        if not self.package_config.upstream_package_name:
            raise PackitException(
                f'"upstream_package_name" is not set: unable to fix the spec file; please set it.'
            )
        new_setup_line += f" -n {self.package_config.upstream_package_name}-{version}"
        logger.debug(
            f"new {'%autosetup' if 'autosetup' in new_setup_line else '%setup'}"
            f" line:\n{new_setup_line}"
        )
        prep[idx] = new_setup_line
        self.specfile.spec_content.replace_section("%prep", prep)
        self.specfile.write_spec_content()

    def _fix_spec_source(self, archive):
        prefix = "Source"
        regex = re.compile(r"^Source\s*:.+$")
        for line in self.specfile.spec_content.section("%package"):
            # we are looking for Source lines
            if line.startswith(prefix):
                # it's a Source line!
                if line.startswith(self.package_config.spec_source_id):
                    # it even matches the specific Source\d+
                    full_name = self.package_config.spec_source_id
                elif regex.match(line):
                    # okay, let's try the other very common default
                    # https://github.com/packit-service/packit/issues/536#issuecomment-534074925
                    full_name = prefix
                else:
                    # nope, let's continue the search
                    continue
                # we found it!
                break
        else:
            raise PackitException(
                "The spec file doesn't have sources set "
                f"via {self.package_config.spec_source_id} nor {prefix}."
            )
        self.specfile.set_tag(full_name, archive)

    def create_srpm(self, srpm_path: str = None, srpm_dir: str = None) -> Path:
        """
        Create SRPM from the actual content of the repo

        :param srpm_path: path to the srpm
        :param srpm_dir: path to the directory where the srpm is meant to be placed
        :return: path to the srpm
        """
        if self.running_in_service():
            srpm_dir = "."
            rpmbuild_dir = "."
            src_dir = str(
                self.absolute_specfile_dir.relative_to(self.local_project.working_dir)
            )
        else:
            srpm_dir = srpm_dir or os.getcwd()
            src_dir = rpmbuild_dir = str(self.absolute_specfile_dir)

        cmd = [
            "rpmbuild",
            "-bs",
            "--define",
            f"_sourcedir {rpmbuild_dir}",
            f"--define",
            f"_srcdir {src_dir}",
            "--define",
            f"_specdir {rpmbuild_dir}",
            "--define",
            f"_srcrpmdir {srpm_dir}",
            # no idea about this one, but tests were failing in tox w/o it
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
        escaped_command = " ".join([f'"{cmd_part}"' for cmd_part in cmd])
        logger.debug(f"SRPM build command: {escaped_command}")
        present_srpms = set(Path(srpm_dir).glob("*.src.rpm"))
        logger.debug("present srpms = %s", present_srpms)
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
            return Path(self.local_project.working_dir).joinpath(the_srpm)
        return Path(the_srpm)

    def _get_srpm_from_rpmbuild_output(self, output: str) -> str:
        """
        Try to find the srpm file in the `rpmbuild -bs` command output.

        :param output: output of the `rpmbuild -bs` command
        :return: the name of the SRPM file
        """
        logger.debug(f"{output}")
        # not doing 'Wrote: (.+)' since people can have different locales; hi Franto!
        reg = r": (.+\.src\.rpm)$"
        try:
            the_srpm = re.findall(reg, output)[0]
        except IndexError:
            raise PackitSRPMNotFoundException(
                "SRPM cannot be found, something is wrong."
            )
        logger.info("SRPM is %s", the_srpm)
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
        upstream_ref = upstream_ref or self.package_config.upstream_ref

        if upstream_ref:
            self.prepare_upstream_using_source_git(upstream_ref)
        else:
            created_archive = self.create_archive(version=current_git_describe_version)
            self.fix_specfile_to_use_local_archive(
                archive=created_archive, archive_version=current_git_describe_version
            )

        # https://github.com/packit-service/packit-service/issues/314
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
            self.add_patches_to_specfile(patches)

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
        out = utils.run_command_remote(
            cmd,
            cwd=self.local_project.working_dir,
            output=True,
            decode=True,
            print_live=True,
        )
        return out
