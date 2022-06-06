# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import shutil
from pathlib import Path
from typing import Optional, Union

import git
from git.exc import GitCommandError
from ogr import GitlabService
from ogr.abstract import GitProject, GitService
from ogr.factory import get_service_class
from ogr.parsing import parse_git_repo

from packit.constants import LP_TEMP_PR_CHECKOUT_NAME
from packit.exceptions import PackitException, PackitMergeException
from packit.utils.repo import (
    RepositoryCache,
    is_git_repo,
    get_repo,
    shorten_commit_hash,
)

logger = logging.getLogger(__name__)


class LocalProject:
    """
    Class representing a cloned repository
    and its API to the remote git-forge (e.g. GitHub/GitLab/Pagure)

    - git_repo: instance of git.Repo
    - working_dir: working directory for the project
    - ref: git ref (branch/tag/commit) if set, then checkouted
    - git_project: instance of ogr.GitProject (remote API for project)
    - git_service: instance of ogr.GitService (tokens for remote API)
    - git_url: remote url (used for cloning)
    - full_name: "$namespace/$repo"
    - namespace: namespace of the remote project
    - repo_name: name of the remote project


    Local project can compute other attributes if it is possible.
    """

    # setting defaults to str because `None == ""` results into TypeError is not true-true
    def __init__(
        self,
        git_repo: git.Repo = None,
        working_dir: Union[Path, str, None] = None,
        ref: str = "",
        git_project: GitProject = None,
        git_service: GitService = None,
        git_url: str = "",
        full_name: str = "",
        namespace: str = "",
        repo_name: str = "",
        offline: bool = False,
        refresh: bool = True,
        remote: str = "",
        pr_id: Optional[str] = None,
        cache: Optional[RepositoryCache] = None,
        merge_pr: bool = True,
        target_branch: str = "",
    ) -> None:
        """

        :param git_repo: git.Repo
        :param working_dir: Path|str (working directory for the project)
        :param ref: str (git ref (branch/tag/commit) if set, then checked out)
        :param git_project: ogr.GitProject (remote API for project)
        :param git_service: ogr.GitService (tokens for remote API)
        :param git_url: str (remote url used for cloning)
        :param full_name: str ("$namespace/$repo")
        :param namespace: str (namespace of the remote project)
        :param repo_name: str (name of the remote project)
        :param offline: bool (do not use any network action, defaults to False)
        :param refresh: bool (calculate the missing attributes, defaults to True)
        :param remote: name of the git remote to use
        :param pr_id: ID of the pull request to fetch and check out
        """
        self.working_dir_temporary = False
        self._git_repo: git.Repo = git_repo
        self.working_dir: Optional[Path] = Path(working_dir) if working_dir else None
        self._ref = ref
        self.git_project = git_project
        self.git_service = git_service
        self.git_url = git_url
        self.full_name = full_name
        self.repo_name = repo_name
        self.namespace = namespace
        self.offline = offline
        self.remote = remote
        self.cache = cache

        logger.debug(
            "Arguments received in the init method of the LocalProject class: \n"
            f"git_repo: {git_repo}\n"
            f"working_dir: {working_dir}\n"
            f"ref: {ref}\n"
            f"git_project: {git_project}\n"
            f"git_service: {git_service}\n"
            f"git_url: {git_url}\n"
            f"full_name: {full_name}\n"
            f"namespace: {namespace}\n"
            f"repo_name: {repo_name}\n"
            f"offline: {offline}\n"
            f"refresh {refresh}\n"
            f"remote: {remote}\n"
            f"pr_id: {pr_id}\n"
            f"cache: {cache}\n"
            f"merge_pr: {merge_pr}\n"
            f"target_branch: {target_branch}\n"
        )

        if refresh:
            self.refresh_the_arguments()

        # p-s gives us both, commit hash for a PR and PR ID as well
        # since we want to have 'pr123' in the release field, let's check out
        # the PR itself, so if both are specified, PR ID > ref
        if pr_id:
            self.checkout_pr(pr_id)
            if merge_pr:
                self.merge_pr(pr_id, target_branch)
            self.checkout_as_pr_branch(pr_id)
        elif ref:
            self.checkout_ref(ref)

    def __repr__(self):
        return (
            "LocalProject("
            f"working_dir_temporary='{self.working_dir_temporary}', "
            f"git_repo='{self.git_repo}', "
            f"working_dir='{self.working_dir}', "
            f"ref='{self.ref}', "
            f"git_project='{self.git_project}', "
            f"git_service='{self.git_service}', "
            f"git_url='{self.git_url}', "
            f"full_name='{self.full_name}', "
            f"repo_name='{self.repo_name}', "
            f"namespace='{self.namespace}', "
            f"offline='{self.offline}', "
            f"remote='{self.remote}', "
            f"commit_hexsha='{self.commit_hexsha}')"
        )

    @property
    def git_repo(self) -> Optional[git.Repo]:
        """The git.Repo tied to this LocalProject.

        This is useful for creating class-level mocks with flexmock rather
        than having to worry about instantiation of the LocalProject class.
        The property can be mocked so that it returns a mock repo with the
        required capabilities.
        """
        return self._git_repo

    @property
    def ref(self) -> Optional[str]:
        """
        Name of the HEAD if the HEAD is not detached,
        else commit hash.
        """
        return self._get_ref_from_git_repo() if self.git_repo else None

    @property
    def commit_hexsha(self) -> str:
        """
        Get the short commit hash for the current commit.

        :return: first 8 characters of the current commit
        """
        if self.git_repo.head.is_detached:
            return shorten_commit_hash(self.git_repo.head.commit.hexsha)
        else:
            return shorten_commit_hash(self.git_repo.active_branch.commit.hexsha)

    def clean(self):
        """Remove the git tree when cloned into a temporary directory"""
        if self.working_dir_temporary:
            logger.debug(f"Cleaning: {self.working_dir}")
            shutil.rmtree(self.working_dir, ignore_errors=True)
            self.working_dir_temporary = False

    def free_resources(self):
        """Clean internal git cache which GitPython uses in the background, suggested solution:
        https://github.com/gitpython-developers/GitPython/issues/546#issuecomment-256657166
        the code of the function clearly manipulates the git-cat-file operations
        which we are seeing hang (source: git.cmd.Git.clear_cache)
        """
        if self.git_repo:  # tests in p-s can have `self.git_repo = None`
            self.git_repo.git.clear_cache()

    def refresh_the_arguments(self):
        change = True
        while change:
            # we are trying to get new information while it is possible
            # new iteration is done only if there was a change in the last iteration

            change = (
                self._parse_repo_name_full_name_and_namespace()
                or self._parse_git_repo_from_working_dir()
                or self._parse_git_project_from_repo_namespace_and_git_service()
                or self._parse_git_service_from_git_project()
                or self._parse_ref_from_git_repo()
                or self._parse_working_dir_from_git_repo()
                or self._parse_git_repo_from_git_url()
                or self._parse_git_url_from_git_project()
                or self._parse_repo_name_from_git_project()
                or self._parse_namespace_from_git_project()
                or self._parse_git_url_from_git_repo()
                or self._parse_namespace_from_git_url()
            )

    def _parse_repo_name_full_name_and_namespace(self):
        change = False
        if self.repo_name and self.namespace and not self.full_name:
            self.full_name = f"{self.namespace}/{self.repo_name}"
            change = True
        if self.full_name and not self.namespace:
            self.namespace = self.full_name.split("/")[0]
            change = True
        if self.full_name and not self.repo_name:
            self.repo_name = self.full_name.split("/")[1]
            change = True

        if change:
            logger.debug(f"Parsed full repo name '{self.namespace}/{self.repo_name}'.")
        return change

    def _parse_git_repo_from_working_dir(self) -> bool:
        """
        Get the repo from the self.working_dir (clone self.git_url if it is not a git repo)
        """
        if self.working_dir and not self.git_repo:
            logger.debug(
                "`working_dir` is set and `git_repo` is not: let's discover..."
            )
            if is_git_repo(directory=self.working_dir):
                logger.debug("It's a git repo!")
                self._git_repo = git.Repo(path=self.working_dir)
                return True

            elif self.git_url and not self.offline:
                self._git_repo = self._get_repo(
                    url=self.git_url, directory=self.working_dir
                )
                logger.debug(
                    f"We just cloned git repo {self.git_url} to {self.working_dir}."
                )
                return True

        return False

    def _parse_git_project_from_repo_namespace_and_git_service(
        self,
    ) -> bool:

        if (
            self.repo_name
            and self.namespace
            and self.git_service
            and not self.git_project
            and not self.offline
        ):
            self.git_project = self.git_service.get_project(
                repo=self.repo_name, namespace=self.namespace
            )
            logger.debug(f"Parsed project '{self.namespace}/{self.repo_name}'.")
            return True
        return False

    def _parse_git_service_from_git_project(self):
        if not (self.git_project is None or self.git_service or self.offline):
            self.git_service = self.git_project.service
            logger.debug(
                f"Parsed service {self.git_service} from the project {self.git_project}."
            )
            return True
        return False

    def _parse_ref_from_git_repo(self):
        if self.git_repo and not self._ref:
            self._ref = self._get_ref_from_git_repo()
            logger.debug(f"Parsed ref {self._ref!r} from the repo {self.git_repo}.")
            return bool(self._ref)
        return False

    def _parse_working_dir_from_git_repo(self):
        if self.git_repo and not self.working_dir:
            self.working_dir = Path(self.git_repo.working_dir)
            logger.debug(
                f"Parsed working directory {self.working_dir} from the repo {self.git_repo}."
            )
            return True
        return False

    def _parse_git_repo_from_git_url(self):
        if (
            self.git_url
            and not self.working_dir
            and not self.git_repo
            and not self.offline
        ):
            self._git_repo = self._get_repo(url=self.git_url)
            self.working_dir_temporary = True
            logger.debug(f"Parsed repo {self.git_repo} from url {self.git_url!r}.")
            return True
        return False

    def _parse_git_url_from_git_project(self):
        if self.git_project and not self.git_url and not self.offline:
            self.git_url = self.git_project.get_git_urls()["git"]
            logger.debug(
                f"Parsed remote url {self.git_url!r} from the project {self.git_project}."
            )
            return True
        return False

    def _parse_repo_name_from_git_project(self):
        if self.git_project and not self.repo_name:
            self.repo_name = self.git_project.repo
            if not self.repo_name:
                raise PackitException(
                    "Repo name should have been set but isn't, this is bug!"
                )
            logger.debug(
                f"Parsed repo name {self.repo_name!r} from the git project {self.git_project}."
            )
            return True
        return False

    def _parse_namespace_from_git_project(self):
        if self.git_project and not self.namespace:
            self.namespace = self.git_project.namespace
            logger.debug(
                f"Parsed namespace {self.namespace!r} from the project {self.git_project}."
            )
            return True
        return False

    def _parse_git_url_from_git_repo(self):
        if not self.git_repo or self.git_url:
            return False

        if self.remote:
            self.git_url = next(self.git_repo.remote(self.remote).urls)
        elif self.git_repo.remotes:
            for remote in self.git_repo.remotes:
                if remote.name == "origin":
                    # origin as a default
                    self.git_url = remote.url
                    break
            else:
                # or use first one
                self.git_url = next(self.git_repo.remotes[0].urls)
        else:
            # Repo has no remotes
            return False
        logger.debug(
            f"Parsed remote url {self.git_url!r} from the repo {self.git_repo}."
        )
        return True

    def _parse_namespace_from_git_url(self):
        if self.git_url and not (self.namespace and self.repo_name):
            parsed_repo_url = parse_git_repo(potential_url=self.git_url)
            if (
                parsed_repo_url.namespace == self.namespace
                and parsed_repo_url.repo == self.repo_name
            ):
                return False
            self.namespace, self.repo_name = (
                parsed_repo_url.namespace,
                parsed_repo_url.repo,
            )
            logger.debug(
                f"Parsed namespace and repo name ({self.namespace}, {self.repo_name}) "
                f"from url {self.git_url!r}."
            )
            return True
        return False

    def _get_ref_from_git_repo(self) -> str:
        if self.git_repo.head.is_detached:
            return self.git_repo.head.commit.hexsha
        else:
            return self.git_repo.active_branch.name

    def _get_repo(self, url, directory=None):
        if self.cache:
            return self.cache.get_repo(url, directory=directory)
        return get_repo(url=url, directory=directory)

    def checkout_ref(self, ref: str):
        """Check out selected ref in the git repo"""
        logger.info(f"Checking out ref {ref!r}.")
        self.git_repo.git.checkout(ref)
        logger.debug(f"Current commit is '{self.git_repo.commit()}'")

    def create_branch(
        self, branch_name: str, base: str = "HEAD", setup_tracking: bool = False
    ) -> git.Head:
        """
        Create a new git branch in git

        :param branch_name: name of the branch to check out and fetch
        :param base: we base our new branch on this one
        :param setup_tracking: set up remote tracking
               (exc will be raised if the branch is not in the remote)
        :return the branch which was just created
        """
        # it's not an error if the branch already exists
        if branch_name in self.git_repo.branches:
            logger.debug(
                f"It seems that branch {branch_name!r} already exists, checking it out."
            )
            head = self.git_repo.branches[branch_name]
        else:
            head = self.git_repo.create_head(branch_name, commit=base)

        if setup_tracking:
            origin = self.git_repo.remote("origin")
            if branch_name in origin.refs:
                remote_ref = origin.refs[branch_name]
            else:
                raise PackitException(
                    f"Remote origin doesn't have ref {branch_name!r}."
                )
            # this is important to fedpkg: build can't find the tracking branch otherwise
            head.set_tracking_branch(remote_ref)

        return head

    def checkout_as_pr_branch(self, pr_id: Union[str, int]) -> None:
        """
        Rename current branch into pr/{pr_id}.

        Args:
            pr_id: ID of the PR we are merging.
        """
        branch = self.git_repo.create_head(f"pr/{pr_id}", "HEAD")
        branch.checkout()

    def _fetch_as_branch(
        self, remote_ref: str, local_ref: str, local_branch: str
    ) -> None:
        """
        Fetches reference from the remote as the specified local reference and
        creates a branch for it.

        Args:
            remote_ref: Git reference to be fetched from remote.
            local_ref: Git reference that refers to the remote reference.
            local_branch: Branch that represents local reference.
        """
        remote = self.remote or "origin"
        self.git_repo.remotes[remote].fetch(f"{remote_ref}:{local_ref}")
        # overwrite the local checkout when needed, remote is always accurate
        self.git_repo.create_head(local_branch, f"{remote}/{local_branch}", force=True)

    def checkout_pr(self, pr_id: Union[str, int]) -> None:
        """
        Fetch selected PR and check it out in a local branch `pr/{pr_id}`.

        Args:
            pr_id: ID of the PR we are merging.
        """
        logger.info(f"Checking out PR {pr_id}.")
        is_gitlab = isinstance(self.git_service, GitlabService) or (
            not self.git_service and get_service_class(self.git_url) == GitlabService
        )
        remote_ref = "+refs/{}/{}/head".format(
            "merge-requests" if is_gitlab else "pull", pr_id
        )
        remote_name = self.remote or "origin"
        local_ref = f"refs/remotes/{remote_name}/{LP_TEMP_PR_CHECKOUT_NAME}/{pr_id}"
        local_branch = f"{LP_TEMP_PR_CHECKOUT_NAME}/{pr_id}"

        self._fetch_as_branch(remote_ref, local_ref, local_branch)
        self.git_repo.branches[local_branch].checkout()

        head_commit = self.git_repo.branches[local_branch].commit
        logger.info(
            f"Checked out commit\n"
            f"({shorten_commit_hash(head_commit.hexsha)})\t{head_commit.summary}"
        )

    def merge_pr(
        self, pr_id: Union[str, int], target_branch_name: Optional[str] = None
    ) -> None:
        """
        Merge given PR into target branch. Fetches and switches to base branch
        (where changes from the PR are to be merged) and then merges branch with
        changes from the PR.

        Args:
            pr_id: ID of the PR we are merging.
            target_branch_name: name of the branch the PR should be merged into if
            git_project is None

        Raises:
            PackitException: In case merge fails.
        """
        remote = self.remote or "origin"
        target_branch_name = (
            self.git_project.get_pr(int(pr_id)).target_branch
            if self.git_project
            else target_branch_name
        )
        if not target_branch_name:
            raise PackitException(
                f"Cannot get the target branch for merging PR {pr_id}."
            )

        logger.debug(f"Target branch: {target_branch_name}")

        self._fetch_as_branch(
            f"+refs/heads/{target_branch_name}",
            f"refs/remotes/{remote}/pr/{pr_id}",
            target_branch_name,
        )
        self.git_repo.branches[target_branch_name].checkout()
        target_branch = self.git_repo.branches[target_branch_name]

        commit_sha = shorten_commit_hash(target_branch.commit.hexsha)
        logger.info(
            f"Merging ({target_branch}) with commit:\n"
            f"({commit_sha})\t{target_branch.commit.summary}"
        )
        try:
            self.git_repo.git.merge(f"{LP_TEMP_PR_CHECKOUT_NAME}/{pr_id}")
        except GitCommandError as ex:
            logger.warning(f"Merge failed with: {ex}")
            if "Merge conflict" in str(ex):
                raise PackitMergeException(ex)
            raise PackitException(ex)

    def checkout_release(self, tag: str) -> None:
        logger.info(f"Checking out upstream version {tag}.")
        try:
            self.git_repo.git.checkout(tag)
        except Exception as ex:
            raise PackitException(f"Cannot checkout release tag: {ex!r}.")

    def fetch(self, remote: str, refspec: Optional[str] = None, force: bool = False):
        """
        Fetch refs and/or tags from a remote to this repo.

        Args:
            remote: Str or path of the repo we fetch from.
            refspec: See man git-fetch.
            force: See --force in man git-fetch.
        """
        args = [remote]
        args += [refspec] if refspec else ["--tags"]
        if force:
            args += ["--force"]
        self.git_repo.git.fetch(*args)

    def __del__(self):
        self.clean()
