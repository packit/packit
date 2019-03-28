import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional, List, Tuple

import git
from ogr.services.github import GithubService
from rebasehelper.exceptions import RebaseHelperError
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
        self.github_token = self.config.github_token
        self.upstream_project_url: str = self.package_config.upstream_project_url
        self.files_to_sync: Optional[List[str]] = self.package_config.synced_files

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
            self._local_project = LocalProject(
                path_or_url=self.upstream_project_url,
                repo_name=self.package_name,
                git_service=GithubService(token=self.github_token),
            )
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

    def create_branch(
        self, branch_name: str, base: str = "HEAD", setup_tracking: bool = False
    ) -> git.Head:
        """
        Create a new git branch in dist-git

        :param branch_name: name of the branch to check out and fetch
        :param base: we base our new branch on this one
        :param setup_tracking: set up remote tracking
                              (exc will be raised if the branch is not in the remote)
        :return the branch which was just created
        """
        # it's not an error if the branch already exists
        origin = self.local_project.git_repo.remote("origin")
        heads = self.local_project.git_repo.heads
        if branch_name in heads:
            logger.debug(f"Branch '{branch_name}' already exists.")
            return heads[branch_name]
        head = self.local_project.git_repo.create_head(branch_name, commit=base)

        if setup_tracking:
            try:
                remote_ref = origin.refs[branch_name]
            except IndexError:
                raise PackitException("Remote origin doesn't have ref %s" % branch_name)
            # this is important to fedpkg: build can't find the tracking branch otherwise
            head.set_tracking_branch(remote_ref)

        return head

    def checkout_branch(self, git_ref: str):
        """
        Perform a `git checkout`

        :param git_ref: ref to check out
        """
        try:
            head = self.local_project.git_repo.heads[git_ref]
        except IndexError:
            raise PackitException(f"Branch {git_ref} does not exist")
        head.checkout()

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

    def commit(self, title: str, msg: str, prefix: str = "[packit] ") -> None:
        """
        Perform `git add -A` and `git commit`
        """
        main_msg = f"{prefix}{title}"
        self.local_project.git_repo.git.add("-A")
        self.local_project.git_repo.index.write()
        commit_args = ["-s", "-m", main_msg]
        if msg:
            commit_args += ["-m", msg]
        self.local_project.git_repo.git.commit(*commit_args)

    def push(
        self,
        branch_name: str,
        force: bool = False,
        fork: bool = True,
        remote_name: str = None,
    ) -> str:
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

        if not remote_name:
            if fork:
                if self.local_project.git_project.is_fork:
                    project = self.local_project.git_project
                else:
                    # ogr is awesome! if you want to fork your own repo, you'll get it!
                    project = self.local_project.git_project.get_fork(create=True)
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
            self.local_project.git_repo.remote(remote_name).push(
                refspec=branch_name, force=force
            )
        except git.GitError as ex:
            msg = (
                f"Unable to push to remote {remote_name} using branch {branch_name}, "
                f"the error is:\n{ex}"
            )
            raise PackitException(msg)
        return str(branch_name)

    def create_pull(
        self, pr_title: str, pr_description: str, source_branch: str, target_branch: str
    ) -> None:
        """
        Create upstream pull request using the requested branches
        """
        project = self.local_project.git_project

        if not self.github_token:
            raise PackitException(
                "Please provide GITHUB_TOKEN as an environment variable."
            )

        if project:
            source_branch = f"{project.namespace}:{source_branch}"
            project = self.local_project.git_project.parent

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
        logger.info(f"Version in upstream registries is {version!r}.")
        return version

    def get_specfile_version(self) -> str:
        """ provide version from specfile """
        version = self.specfile.get_version()
        logger.info(f"Version in spec file is {version!r}.")
        return version

    def sync_files(self, downstream_project: LocalProject) -> None:
        """
        sync required files from upstream to downstream
        """
        logger.debug("about to sync files %s", self.files_to_sync)
        for fi in self.files_to_sync:
            # TODO: fi can be dir
            fi = fi[1:] if fi.startswith("/") else fi
            src = os.path.join(downstream_project.working_dir, fi)
            if os.path.exists(src):
                logger.info("syncing %s", src)
                shutil.copy2(src, self.local_project.working_dir)
            else:
                raise PackitException(
                    f"File {src} is not present in the downstream repository. "
                    f"Upstream ref {downstream_project.git_repo.active_branch} is checked out"
                )

    def get_version(self) -> str:
        """
        Return version of the latest release available: prioritize upstream
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

    def get_current_version(self) -> str:
        """
        Get version of the project in current state (hint `git describe`)

        :return: e.g. 0.1.1.dev86+ga17a559.d20190315 or 0.6.1.1.gce4d84e
        """
        ver = run_command(
            self.package_config.current_version_command, output=True
        ).strip()
        logger.debug("version = %s", ver)
        # FIXME: this might not work when users expect the dashes
        #  but! RPM refuses dashes in version/release
        ver = ver.replace("-", ".")
        logger.debug("sanitized version = %s", ver)
        return ver

    def bump_spec(self, version: str = None, changelog_entry: str = None):
        """
        Run rpmdev-bumpspec on the upstream spec file: it enables
        changing version and adding a changelog entry

        :param version: new version which should be present in the spec
        :param changelog_entry: new changelog entry (just the comment)
        """
        cmd = ["rpmdev-bumpspec"]
        if version:
            # 1.2.3-4 means, version = 1.2.3, release = 4
            cmd += ["--new", version]
        if changelog_entry:
            cmd += ["--comment", changelog_entry]
        cmd.append(self.specfile_path)
        run_command(cmd)

    def set_spec_version(self, version: str, changelog_entry: str):
        """
        Set version in spec and add a changelog_entry.

        :param version: new version
        :param changelog_entry: accompanying changelog entry
        """
        try:
            # also this code adds 3 rpmbuild dirs into the upstream repo,
            # we should ask rebase-helper not to do that
            self.specfile.set_version(version=version)
            self.specfile.changelog_entry = changelog_entry
            # https://github.com/rebase-helper/rebase-helper/blob/643dab4a864288327289f34e023124d5a499e04b/rebasehelper/application.py#L446-L448
            new_log = self.specfile.get_new_log()
            new_log.extend(self.specfile.spec_content.sections["%changelog"])
            self.specfile.spec_content.sections["%changelog"] = new_log
            self.specfile.save()
        except RebaseHelperError as ex:
            logger.error(f"rebase-helper failed to change the spec file: {ex!r}")
            raise PackitException("rebase-helper didn't do the job")

    def create_archive(self):
        """
        Create archive, using `git archive` by default, from the content of the upstream
        repository, only committed changes are present in the archive
        """
        if self.package_config.upstream_project_name:
            dir_name = f"{self.package_config.upstream_project_name}-{self.get_current_version()}"
        else:
            dir_name = f"{self.package_name}-{self.get_current_version()}"
        logger.debug("name + version = %s", dir_name)
        # We don't care about the name of the archive, really
        # we just require for the archive to be placed in the cwd
        if self.package_config.create_tarball_command:
            archive_cmd = self.package_config.create_tarball_command
        else:
            # FIXME: .tar.gz is naive
            archive_name = f"{dir_name}.tar.gz"
            archive_cmd = [
                "git",
                "archive",
                "-o",
                archive_name,
                "--prefix",
                f"{dir_name}/",
                "HEAD",
            ]
        run_command(archive_cmd)

    def create_srpm(self, srpm_path: str = None) -> Path:
        """
        Create SRPM from the actual content of the repo

        :param srpm_path: path to the srpm
        :return: path to the srpm
        """
        cwd = os.getcwd()
        cmd = [
            "rpmbuild",
            "-bs",
            "--define",
            f"_sourcedir {cwd}",
            "--define",
            f"_specdir {cwd}",
            "--define",
            f"_srcrpmdir {cwd}",
            # no idea about this one, but tests were failing in tox w/o it
            "--define",
            f"_topdir {cwd}",
            # we also need these 3 so that rpmbuild won't create them
            "--define",
            f"_builddir {cwd}",
            "--define",
            f"_rpmdir {cwd}",
            "--define",
            f"_buildrootdir {cwd}",
            self.specfile_path,
        ]
        present_srpms = set(Path.cwd().glob("*.src.rpm"))
        logger.debug("present srpms = %s", present_srpms)
        out = run_command(
            cmd,
            output=True,
            error_message="SRPM could not be created. Is the archive present?",
        ).strip()
        logger.debug(f"{out}")
        # not doing 'Wrote: (.+)' since people can have different locales; hi Franto!
        reg = r": (.+\.src\.rpm)$"
        try:
            the_srpm = re.findall(reg, out)[0]
        except IndexError:
            raise PackitException("SRPM cannot be found, something is wrong.")
        if srpm_path:
            Path(the_srpm).rename(srpm_path)
            return Path(srpm_path)
        return Path(the_srpm)
