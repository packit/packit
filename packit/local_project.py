# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import dataclasses
import logging
import shutil
from collections.abc import Iterable
from functools import partial
from pathlib import Path
from typing import Any, ClassVar, Optional, TypeVar, Union

import git
from git.exc import GitCommandError
from ogr import GitlabService
from ogr.abstract import GitProject, GitService
from ogr.factory import get_project, get_service_class
from ogr.parsing import parse_git_repo

from packit.constants import LP_TEMP_PR_CHECKOUT_NAME
from packit.exceptions import PackitException, PackitMergeException
from packit.utils.repo import (
    RepositoryCache,
    get_repo,
    is_git_repo,
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
        git_repo: Optional[git.Repo] = None,
        working_dir: Union[Path, str, None] = None,
        ref: str = "",
        git_project: Optional[GitProject] = None,
        git_service: Optional[GitService] = None,
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
        working_dir_temporary: bool = False,
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
        self.working_dir_temporary = working_dir_temporary
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
            f"target_branch: {target_branch}\n",
        )

        if refresh:
            self.refresh_the_arguments()

        # skip checkouts if the git repo is not present
        if not self.git_repo:
            return

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
    def commit_hexsha(self) -> Optional[str]:
        """
        Get the short commit hash for the current commit.

        :return: first 8 characters of the current commit
        """
        if not self.git_repo:
            return None
        if self.git_repo.head.is_detached:
            return shorten_commit_hash(self.git_repo.head.commit.hexsha)
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
        # TODO: remove this whole logic once everything uses LocalProjectBuilder
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
                "`working_dir` is set and `git_repo` is not: let's discover...",
            )
            if is_git_repo(directory=self.working_dir):
                logger.debug("It's a git repo!")
                self._git_repo = git.Repo(path=self.working_dir)
                return True

            if self.git_url and not self.offline:
                self._git_repo = self._get_repo(
                    url=self.git_url,
                    directory=self.working_dir,
                )
                logger.debug(
                    f"We just cloned git repo {self.git_url} to {self.working_dir}.",
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
                repo=self.repo_name,
                namespace=self.namespace,
            )
            logger.debug(f"Parsed project '{self.namespace}/{self.repo_name}'.")
            return True
        return False

    def _parse_git_service_from_git_project(self):
        if not (self.git_project is None or self.git_service or self.offline):
            self.git_service = self.git_project.service
            logger.debug(
                f"Parsed service {self.git_service} from the project {self.git_project}.",
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
                f"Parsed working directory {self.working_dir} from the repo {self.git_repo}.",
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
                f"Parsed remote url {self.git_url!r} from the project {self.git_project}.",
            )
            return True
        return False

    def _parse_repo_name_from_git_project(self):
        if self.git_project and not self.repo_name:
            self.repo_name = self.git_project.repo
            if not self.repo_name:
                raise PackitException(
                    "Repo name should have been set but isn't, this is bug!",
                )
            logger.debug(
                f"Parsed repo name {self.repo_name!r} from the git project {self.git_project}.",
            )
            return True
        return False

    def _parse_namespace_from_git_project(self):
        if self.git_project and not self.namespace:
            self.namespace = self.git_project.namespace
            logger.debug(
                f"Parsed namespace {self.namespace!r} from the project {self.git_project}.",
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
            f"Parsed remote url {self.git_url!r} from the repo {self.git_repo}.",
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
                f"from url {self.git_url!r}.",
            )
            return True
        return False

    def _get_ref_from_git_repo(self) -> str:
        if self.git_repo.head.is_detached:
            return self.git_repo.head.commit.hexsha
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
        self,
        branch_name: str,
        base: str = "HEAD",
        setup_tracking: bool = False,
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
                f"It seems that branch {branch_name!r} already exists, checking it out.",
            )
            head = self.git_repo.branches[branch_name]
        else:
            head = self.git_repo.create_head(branch_name, commit=base)
            logger.debug(f"Created branch {branch_name}")

        logger.debug(f"HEAD is now at {head.commit.hexsha} {head.commit.summary}")

        if setup_tracking:
            origin = self.git_repo.remote("origin")
            if branch_name in origin.refs:
                remote_ref = origin.refs[branch_name]
            else:
                raise PackitException(
                    f"Remote origin doesn't have ref {branch_name!r}.",
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
        self,
        remote_ref: str,
        local_ref: str,
        local_branch: str,
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
            "merge-requests" if is_gitlab else "pull",
            pr_id,
        )
        remote_name = self.remote or "origin"
        local_ref = f"refs/remotes/{remote_name}/{LP_TEMP_PR_CHECKOUT_NAME}/{pr_id}"
        local_branch = f"{LP_TEMP_PR_CHECKOUT_NAME}/{pr_id}"

        self._fetch_as_branch(remote_ref, local_ref, local_branch)
        self.git_repo.branches[local_branch].checkout()

        head_commit = self.git_repo.branches[local_branch].commit
        logger.info(
            f"Checked out commit\n"
            f"({shorten_commit_hash(head_commit.hexsha)})\t{head_commit.summary}",
        )

    def merge_pr(
        self,
        pr_id: Union[str, int],
        target_branch_name: Optional[str] = None,
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
                f"Cannot get the target branch for merging PR {pr_id}.",
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
            f"({commit_sha})\t{target_branch.commit.summary}",
        )
        try:
            self.git_repo.git.merge(f"{LP_TEMP_PR_CHECKOUT_NAME}/{pr_id}")
        except GitCommandError as ex:
            logger.warning(f"Merge failed with: {ex}")
            if "Merge conflict" in str(ex):
                raise PackitMergeException(ex) from ex
            raise PackitException(ex) from ex

    def checkout_release(self, tag: str) -> None:
        logger.info(f"Checking out upstream version {tag}.")
        try:
            self.git_repo.git.checkout(tag)
        except Exception as ex:
            raise PackitException(
                "Cannot checkout release tag. Please, check whether the "
                "'upstream_tag_template' needs to be configured.",
            ) from ex

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


@dataclasses.dataclass
class LocalProjectCalculationState:
    """Class representing the current state of construction of LocalProject.

    Encloses all the arguments that will then be passed to LocalProject's
    constructor.
    """

    remote: str = ""
    git_repo: Optional[git.Repo] = None
    working_dir: Union[Path, str, None] = None
    ref: str = ""
    git_project: Optional[GitProject] = None
    git_service: Optional[GitService] = None
    git_url: str = ""
    full_name: str = ""
    namespace: str = ""
    repo_name: str = ""
    working_dir_temporary: bool = False

    @classmethod
    def from_local_project(cls, lp: LocalProject) -> "LocalProjectCalculationState":
        """Constructs the calculation state from an existing LocalProject."""
        return cls(
            lp.remote,
            lp.git_repo,
            lp.working_dir,
            lp.ref,
            lp.git_project,
            lp.git_service,
            lp.git_url,
            lp.full_name,
            lp.namespace,
            lp.repo_name,
        )


# Use an explicit sentinel class to have stricter type-checking than just object()
class _CalculateType:
    pass


CALCULATE = _CalculateType()
NOT_TO_CALCULATE = _CalculateType()


T = TypeVar("T")
CanCalculate = Union[T, _CalculateType]


class LocalProjectBuilder:
    """Class for building instances of LocalProject dynamically."""

    PREREQUISITES: ClassVar = {
        "git_repo": ["working_dir", "git_url"],
        "git_project": ["git_url", "repo_name", "namespace", "git_service"],
        "git_service": ["git_project"],
        "ref": ["git_repo"],
        "working_dir": ["git_repo"],
        "git_url": ["git_project", "git_repo"],
        "repo_name": ["git_project", "full_name"],
        "namespace": ["git_project", "git_url", "full_name"],
        "full_name": ["namespace", "repo_name"],
    }

    def __init__(
        self,
        cache: Optional[RepositoryCache] = None,
        instances: Optional[Iterable[GitService]] = None,
        offline: bool = False,
    ):
        """Creates a builder instance.

        Args:
            cache: Repository cache that may be used for getting repos.
            instances: List of GitService instances to utilise while building.
            offline: Whether only offline operations should be performed in this builder.
        """
        self._instances = instances or []
        self._cache = cache
        self.offline = offline

    def _add_prerequisites_to_calculations(
        self,
        to_calculate: set[str],
        not_to_calculate: Optional[set[str]] = None,
    ) -> None:
        """Adds calculation prerequisites into to_calculate set.

        If a caller of this class requests git_repo to be calculated, they should not
        have to care about the prerequisites to git_repo, hence we add those to the
        calculation set as well.
        """
        logger.debug(f"Attributes requested: {', '.join(to_calculate)}")
        logger.debug(
            f"Attributes requested not to be calculated: {', '.join(not_to_calculate)}",
        )
        dependencies = {}
        change = True
        while change:
            len_before = len(to_calculate)
            for calc in to_calculate.copy():
                required = set(self.PREREQUISITES.get(calc, []))
                new_dependencies = required - to_calculate
                if not_to_calculate:
                    new_dependencies -= not_to_calculate
                to_calculate.update(new_dependencies)
                dependencies[calc] = new_dependencies
            change = len(to_calculate) > len_before

        dep_list = [f"{k} => {v}" for k, v in dependencies.items()]
        logger.debug(f"Transitive dependencies: {', '.join(dep_list)}")

    def _refresh_the_state(
        self,
        state: LocalProjectCalculationState,
        to_calculate: set[str],
        not_to_calculate: Optional[set[str]] = None,
    ) -> None:
        """Calculates the requested attributes while also considering transitive relations.

        Args:
            state: The initial state which will be updated with new calculated data.
            to_calculate: Set of attributes that need to be calculated.
        """
        self._add_prerequisites_to_calculations(to_calculate, not_to_calculate)
        # Remove the already set pieces
        to_calculate = set(filter(lambda a: not getattr(state, a, None), to_calculate))
        logger.debug(f"To-calculate set: {to_calculate}")
        name_partial = partial(self._parse_repo_name_full_name_and_namespace)
        all_partials = {
            "git_repo": [
                partial(self._parse_git_repo_from_git_url),
                partial(self._parse_git_repo_from_working_dir),
            ],
            "git_project": [
                partial(self._parse_git_project_from_url),
                partial(self._parse_git_project_from_repo_namespace_and_git_service),
            ],
            "git_service": [partial(self._parse_git_service_from_git_project)],
            "ref": [partial(self._parse_ref_from_git_repo)],
            "working_dir": [partial(self._parse_working_dir_from_git_repo)],
            "git_url": [
                partial(self._parse_git_url_from_git_project),
                partial(self._parse_git_url_from_git_repo),
            ],
            "repo_name": [
                name_partial,
                partial(self._parse_repo_name_from_git_project),
            ],
            "namespace": [
                name_partial,
                partial(self._parse_namespace_from_git_project),
                partial(self._parse_namespace_from_git_url),
            ],
            "full_name": [name_partial],
        }

        partials = [
            part for calc in to_calculate for part in all_partials.get(calc, [])
        ]
        change = True
        while change:
            change = False
            for part in partials:
                change = change or part(state)

    def _parse_repo_name_full_name_and_namespace(
        self,
        state: LocalProjectCalculationState,
    ) -> bool:
        """Calculates repo name, namespace or full name if they are missing
        based on the other attributes."""
        change = False
        if state.repo_name and state.namespace and not state.full_name:
            state.full_name = f"{state.namespace}/{state.repo_name}"
            change = True
        if state.full_name and not state.namespace:
            state.namespace = state.full_name.split("/")[0]
            change = True
        if state.full_name and not state.repo_name:
            state.repo_name = state.full_name.split("/")[1]
            change = True

        if change:
            logger.debug(
                f"Parsed full repo name '{state.namespace}/{state.repo_name}'.",
            )
        return change

    def _parse_git_repo_from_working_dir(
        self,
        state: LocalProjectCalculationState,
    ) -> bool:
        """Prepares git.Repo instance based on working_dir.

        Clones git_url if working_dir is not a repo.
        """
        if state.working_dir and not state.git_repo:
            logger.debug(
                "`working_dir` is set and `git_repo` is not: let's discover...",
            )
            if is_git_repo(directory=state.working_dir):
                logger.debug("It's a git repo!")
                state.git_repo = git.Repo(path=state.working_dir)
                return True

            if state.git_url and not self.offline:
                state.git_repo = self._get_repo(
                    url=state.git_url,
                    directory=state.working_dir,
                )
                logger.debug(
                    f"We just cloned git repo {state.git_url} to {state.working_dir}.",
                )
                return True

        return False

    def _parse_git_project_from_url(self, state: LocalProjectCalculationState) -> bool:
        """Creates GitProject based on git_url and provided GitService instances."""
        if state.git_url and self._instances:
            state.git_project = get_project(
                state.git_url,
                custom_instances=self._instances,
            )
            return True
        return False

    def _parse_git_project_from_repo_namespace_and_git_service(
        self,
        state: LocalProjectCalculationState,
    ) -> bool:
        """Creates GitProject based on namespace, repo name and GitService."""

        if (
            state.repo_name
            and state.namespace
            and state.git_service
            and not state.git_project
            and not self.offline
        ):
            state.git_project = state.git_service.get_project(
                repo=state.repo_name,
                namespace=state.namespace,
            )
            logger.debug(f"Parsed project '{state.namespace}/{state.repo_name}'.")
            return True
        return False

    def _parse_git_service_from_git_project(
        self,
        state: LocalProjectCalculationState,
    ) -> bool:
        """Creates GitService based on GitProject."""
        if not (state.git_project is None or state.git_service or self.offline):
            state.git_service = state.git_project.service
            logger.debug(
                f"Parsed service {state.git_service} from the project {state.git_project}.",
            )
            return True
        return False

    def _parse_ref_from_git_repo(self, state: LocalProjectCalculationState) -> bool:
        """Obtains the current git ref from git.Repo."""
        if state.git_repo and not state.ref:
            state.ref = self._get_ref_from_git_repo(state.git_repo)
            logger.debug(f"Parsed ref {state.ref!r} from the repo {state.git_repo}.")
            return bool(state.ref)
        return False

    def _parse_working_dir_from_git_repo(
        self,
        state: LocalProjectCalculationState,
    ) -> bool:
        """Obtains the working_dir from git.Repo instance."""
        if state.git_repo and not state.working_dir:
            state.working_dir = Path(state.git_repo.working_dir)
            logger.debug(
                f"Parsed working directory {state.working_dir} from the repo {state.git_repo}.",
            )
            return True
        return False

    def _parse_git_repo_from_git_url(self, state: LocalProjectCalculationState) -> bool:
        """Prepares git.Repo instance based on a git URL."""
        if (
            state.git_url
            and not state.working_dir
            and not state.git_repo
            and not self.offline
        ):
            state.git_repo = self._get_repo(url=state.git_url)
            state.working_dir_temporary = True
            logger.debug(f"Parsed repo {state.git_repo} from url {state.git_url!r}.")
            return True
        return False

    def _parse_git_url_from_git_project(
        self,
        state: LocalProjectCalculationState,
    ) -> bool:
        """Obtains git URL from a GitProject."""
        if state.git_project and not state.git_url and not self.offline:
            state.git_url = state.git_project.get_git_urls()["git"]
            logger.debug(
                f"Parsed remote url {state.git_url!r} from the project {state.git_project}.",
            )
            return True
        return False

    def _parse_repo_name_from_git_project(
        self,
        state: LocalProjectCalculationState,
    ) -> bool:
        """Obtains git repo name from a GitProject."""
        if state.git_project and not state.repo_name:
            state.repo_name = state.git_project.repo
            if not state.repo_name:
                raise PackitException(
                    "Repo name should have been set but isn't, this is bug!",
                )
            logger.debug(
                f"Parsed repo name {state.repo_name!r} from the git project {state.git_project}.",
            )
            return True
        return False

    def _parse_namespace_from_git_project(
        self,
        state: LocalProjectCalculationState,
    ) -> bool:
        """Obtains git repo namespace from a GitProject."""
        if state.git_project and not state.namespace:
            state.namespace = state.git_project.namespace
            logger.debug(
                f"Parsed namespace {state.namespace!r} from the project {state.git_project}.",
            )
            return True
        return False

    def _parse_git_url_from_git_repo(self, state: LocalProjectCalculationState) -> bool:
        """Obtains git URL from git.Repo based on the set remote."""
        if not state.git_repo or state.git_url:
            return False

        if state.remote:
            state.git_url = next(state.git_repo.remote(state.remote).urls)
        elif state.git_repo.remotes:
            for remote in state.git_repo.remotes:
                if remote.name == "origin":
                    # origin as a default
                    state.git_url = remote.url
                    break
            else:
                # or use first one
                state.git_url = next(state.git_repo.remotes[0].urls)
        else:
            # Repo has no remotes
            return False
        logger.debug(
            f"Parsed remote url {state.git_url!r} from the repo {state.git_repo}.",
        )
        return True

    def _parse_namespace_from_git_url(
        self,
        state: LocalProjectCalculationState,
    ) -> bool:
        """Obtains git repo namespace from a git URL."""
        if state.git_url and not (state.namespace and state.repo_name):
            parsed_repo_url = parse_git_repo(potential_url=state.git_url)
            if (
                parsed_repo_url.namespace == state.namespace
                and parsed_repo_url.repo == state.repo_name
            ):
                return False
            state.namespace, state.repo_name = (
                parsed_repo_url.namespace,
                parsed_repo_url.repo,
            )
            logger.debug(
                f"Parsed namespace and repo name ({state.namespace}, {state.repo_name}) "
                f"from url {state.git_url!r}.",
            )
            return True
        return False

    @staticmethod
    def _get_ref_from_git_repo(git_repo: git.Repo) -> str:
        if git_repo.head.is_detached:
            return git_repo.head.commit.hexsha
        return git_repo.active_branch.name

    def _get_repo(self, url, directory=None):
        if self._cache:
            return self._cache.get_repo(url, directory=directory)
        return get_repo(url=url, directory=directory)

    def build(
        self,
        # Non-building stuff
        remote: str = "",
        pr_id: Optional[str] = None,
        merge_pr: bool = True,
        target_branch: str = "",
        # Building data/instructions
        git_repo: CanCalculate[Union[git.Repo, None]] = None,
        working_dir: CanCalculate[Union[Path, str, None]] = None,
        ref: CanCalculate[str] = "",
        git_project: CanCalculate[Union[GitProject, None]] = None,
        git_service: CanCalculate[Union[GitService, None]] = None,
        git_url: CanCalculate[str] = "",
        full_name: CanCalculate[str] = "",
        namespace: CanCalculate[str] = "",
        repo_name: CanCalculate[str] = "",
        # LocalProject "template"
        local_project: Optional[LocalProject] = None,
    ) -> LocalProject:
        """Builds the LocalProject instance from the provided attributes.

        Most arguments can either take an explicit value, None (or empty string) or
        they can be passed the sentinel value CALCULATE to signal that this attribute
        must be present in the final LocalProject object and therefore be computed
        dynamically based on the rest of the information.

        Args:
            remote: Name of the git remote to use.
            pr_id: ID of the pull request to fetch and check out.
            merge_pr: Whether the fetched pull request should be merged.
            target_branch: Name of the branch the PR should be merged into.
            git_repo: Instance of git.Repo.
            working_dir: Path to the working directory of the project.
            ref: Git ref, if set, it will be checked out.
            git_project: ogr.GitProject (remote API)
            git_service: ogr.Gitservice (tokens for remote API)
            git_url: URL of the git project (used for cloning)
            full_name: Full name of the remote git project (including namespace).
            repo_name: Name of the remote git project.
            namespace: Namespace of the remote git project.
            local_project: LocalProject to use as the initial calculation state,
                the other arguments will override information present in this LocalProject.

        Returns:
            The constructed LocalProject instance.

        Examples:
            Clone the given URL and checkout the develop branch.

                builder.build(
                    git_url="https://github.com/packit/hello-world",
                    git_repo="CALCULATE",
                    ref="develop",
                )
        """
        to_calculate: set[str] = set()
        not_to_calculate: set[str] = set()

        def check_and_set(
            calc_state: LocalProjectCalculationState,
            attr: str,
            value: Any,
        ):
            if value is CALCULATE:
                to_calculate.add(attr)
            elif value is NOT_TO_CALCULATE:
                not_to_calculate.add(attr)
            elif value is not None and value != "":
                setattr(calc_state, attr, value)

        if local_project:
            state = LocalProjectCalculationState.from_local_project(local_project)
        else:
            state = LocalProjectCalculationState()
        check_and_set(state, "remote", remote)
        check_and_set(state, "git_repo", git_repo)
        check_and_set(state, "working_dir", working_dir)
        check_and_set(state, "ref", ref)
        check_and_set(state, "git_project", git_project)
        check_and_set(state, "git_service", git_service)
        check_and_set(state, "git_url", git_url)
        check_and_set(state, "full_name", full_name)
        check_and_set(state, "namespace", namespace)
        check_and_set(state, "repo_name", repo_name)
        self._refresh_the_state(state, to_calculate, not_to_calculate)
        # dataclasses.asdict cannot be used because some parts of the calculation state
        # are not deep-copyable (git.Repo and possibly ogr objects). A shallow copy suffices.
        state_dict = {
            field.name: getattr(state, field.name)
            for field in dataclasses.fields(state)
        }
        # Do not refresh the built local project (the logic will go away)
        return LocalProject(
            offline=self.offline,
            pr_id=pr_id,
            merge_pr=merge_pr,
            target_branch=target_branch,
            refresh=False,
            cache=self._cache,
            **state_dict,
        )
