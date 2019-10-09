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
from typing import Optional, List, Tuple, Union

import git
from packaging import version
from rebasehelper.exceptions import RebaseHelperError

from packit.utils import is_a_git_ref, run_command, git_remote_url_to_https_url

try:
    from rebasehelper.plugins.plugin_manager import plugin_manager
except ImportError:
    from rebasehelper.versioneer import versioneers_runner

from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.config import Config, PackageConfig, SyncFilesConfig
from packit.constants import COMMON_ARCHIVE_EXTENSIONS
from packit.exceptions import PackitException, FailedCreateSRPM
from packit.local_project import LocalProject

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
        if add_usptream_head_commit:
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

        if self.local_project.git_project.is_fork:
            source_branch = f"{project.namespace}:{source_branch}"
            project = self.local_project.git_project.parent
        elif fork_username:
            source_branch = f"{fork_username}:{source_branch}"

        try:
            upstream_pr = project.pr_create(
                title=pr_title,
                body=pr_description,
                source_branch=source_branch,
                target_branch=target_branch,
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
        commits = self.get_commits_to_upstream(upstream, add_usptream_head_commit=True)

        destination = destination or self.local_project.working_dir

        patches_to_create = []
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
            ] + [
                f":(exclude){sync_file.src}"
                for sync_file in self.package_config.synced_files.get_raw_files_to_sync(
                    Path(self.local_project.working_dir),
                    Path(
                        # this is not important, we only care about src
                        destination
                    ),
                )
            ]
            diff = run_command(
                cmd=git_diff_cmd, cwd=self.local_project.working_dir, output=True
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
            with open(patch_path, mode="w") as patch_file:
                patch_file.write(diff)
            patch_list.append((patch_name, patch_msg))

        return patch_list

    def get_latest_released_version(self) -> str:
        """
        Return version of the upstream project for the latest official release

        :return: the version string (e.g. "1.0.0")
        """
        try:
            get_version = plugin_manager.versioneers.run
        except NameError:
            get_version = versioneers_runner.run

        version = get_version(
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
            return action_output[-1]

        ver = self.command_handler.run_command(
            self.package_config.current_version_command, return_output=True
        ).strip()
        logger.debug("version = %s", ver)
        # RPM refuses dashes in version/release
        ver = ver.replace("-", ".")
        logger.debug("sanitized version = %s", ver)
        return ver

    def bump_spec(
        self,
        version: str = None,
        changelog_entry: str = None,
        bump_release: bool = False,
    ):
        """
        Run rpmdev-bumpspec on the upstream spec file: it enables
        changing version and adding a changelog entry

        :param version: new version which should be present in the spec
        :param changelog_entry: new changelog entry (just the comment)
        :param bump_release: "bump trailing .<DIGIT> component if found, append .1 if not"
                             from the rpmdev-bumpspec --help
        """
        cmd = ["rpmdev-bumpspec"]
        if version:
            # 1.2.3-4 means, version = 1.2.3, release = 4
            cmd += ["--new", version]
        if changelog_entry:
            cmd += ["--comment", changelog_entry]
        if bump_release:
            cmd += ["-r"]
        cmd.append(str(self.absolute_specfile_path))
        run_command(cmd)

    def set_spec_version(
        self, version: str = None, release: str = None, changelog_entry: str = None
    ):
        """
        Set version in spec and add a changelog_entry.

        :param version: new version
        :param changelog_entry: accompanying changelog entry
        """
        try:
            if version:
                # also this code adds 3 rpmbuild dirs into the upstream repo,
                # we should ask rebase-helper not to do that
                self.specfile.set_version(version=version)

            if release:
                self.specfile.set_release_number(release=release)

            if not changelog_entry:
                return

            if not self.specfile.spec_content.section("%changelog"):
                logger.debug(
                    "The specfile doesn't have any %changelog, will not set it."
                )
                return

            if hasattr(self.specfile, "update_changelog"):
                # new rebase helper
                self.specfile.update_changelog(changelog_entry)
            else:
                # old rebase helper
                self.specfile.changelog_entry = changelog_entry
                new_log = self.specfile.get_new_log()
                new_log.extend(self.specfile.spec_content.sections["%changelog"])
                self.specfile.spec_content.sections["%changelog"] = new_log
                self.specfile.save()

        except RebaseHelperError as ex:
            logger.error(f"rebase-helper failed to change the spec file: {ex!r}")
            raise PackitException("rebase-helper didn't do the job")

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
        repository, only committed changes are present in the archive
        """
        version = version or self.get_current_version()

        if self.package_config.upstream_package_name:
            dir_name = f"{self.package_config.upstream_package_name}-{version}"
        else:
            dir_name = f"{self.package_config.downstream_package_name}-{version}"
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
            # one of the returned strings has to contain existing archive name
            for archive_name in reversed(outputs):
                if Path(archive_name.strip()).is_file():
                    logger.info(f"Created archive: {archive_name.strip()}")
                    return archive_name
            else:
                raise PackitException(
                    "No existing file in create-archive action output."
                )

        archive_extension = self.get_archive_extension(dir_name, version)
        if archive_extension not in COMMON_ARCHIVE_EXTENSIONS:
            raise PackitException(
                "The target archive doesn't use a common extension ({}), "
                "git archive can't be used. Please provide your own script "
                "for archive creation.".format(", ".join(COMMON_ARCHIVE_EXTENSIONS))
            )
        archive_name = f"{dir_name}{archive_extension}"

        if self.package_config.create_tarball_command:
            archive_cmd = self.package_config.create_tarball_command
        else:
            archive_cmd = [
                "git",
                "archive",
                "-o",
                archive_name,
                "--prefix",
                f"{dir_name}/",
                "HEAD",
            ]
        self.command_handler.run_command(archive_cmd, return_output=True, env=env)
        return archive_name

    def fix_spec(self, archive: str, version: str, commit: str):
        """
        In order to create a SRPM from current git checkout, we need to have the spec reference
        the tarball and unpack it. This method updates the spec so it's possible.

        :param archive: relative path to the archive: used as Source0
        :param version: version to set in the spec
        :param commit: commit to set in the changelog
        """
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
        self.specfile._write_spec_content()

        msg = f"Development snapshot ({commit})"
        self.bump_spec(version=f"{version}", changelog_entry=msg, bump_release=True)

    def create_srpm(
        self,
        srpm_path: str = None,
        source_dir: Union[str, Path] = None,
        srpm_dir: str = None,
    ) -> Path:
        """
        Create SRPM from the actual content of the repo

        :param source_dir: path with the source files (defaults to dir with specfile)
        :param srpm_path: path to the srpm
        :param srpm_dir: path to the directory where the srpm is meant to be placed
        :return: path to the srpm
        """
        if self.running_in_service():
            srpm_dir = "."
            rpmbuild_dir = "."
        else:
            srpm_dir = srpm_dir or os.getcwd()
            rpmbuild_dir = str(self.absolute_specfile_dir)
        cmd = [
            "rpmbuild",
            "-bs",
            "--define",
            f"_sourcedir {source_dir or rpmbuild_dir}",
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
        present_srpms = set(Path(srpm_dir).glob("*.src.rpm"))
        logger.debug("present srpms = %s", present_srpms)
        try:
            out = self.command_handler.run_command(cmd, return_output=True).strip()
        except PackitException as ex:
            logger.error(f"Failed to create SRPM: {ex!r}")
            raise FailedCreateSRPM("Failed to create SRPM.")
        logger.debug(f"{out}")
        # not doing 'Wrote: (.+)' since people can have different locales; hi Franto!
        reg = r": (.+\.src\.rpm)$"
        try:
            the_srpm = re.findall(reg, out)[0]
        except IndexError:
            raise PackitException("SRPM cannot be found, something is wrong.")
        logger.info("SRPM is %s", the_srpm)
        if srpm_path:
            shutil.move(the_srpm, srpm_path)
            return Path(srpm_path)
        if self.running_in_service():
            return Path(self.local_project.working_dir).joinpath(the_srpm)
        return Path(the_srpm)
