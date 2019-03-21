import logging
import os
import shutil

import git
import requests

from ogr.abstract import GitProject, GitService
from packit.utils import is_git_repo, get_repo, get_namespace

logger = logging.getLogger(__name__)


class LocalProject:
    """
    Class representing the cloned repository and the remote API

    - git_repo: instance of git.Repo
    - working_dir: working directory for the project
    - ref: git ref (branch/tag/commit) if set, then checkouted
    - git_project: instance of ogr.GitProject (remote API for project)
    - git_service: instance of ogr.GitService (tokens for remote API)
    - git_url: remote url (used for cloning)
    - full_name: "$namespace/$repo"
    - namespace: namespace of the remote project
    - repo_name: name of the remote project
    - path_or_url: working_dir if the directory exists
                    and git_url if the request is valid


    Local project can compute other attributes if it is possible.
    """

    def __init__(
        self,
        git_repo: git.Repo = None,
        working_dir: str = None,
        ref: str = None,
        git_project: GitProject = None,
        git_service: GitService = None,
        git_url: str = None,
        full_name: str = None,
        namespace: str = None,
        repo_name: str = None,
        path_or_url: str = None,
        offline: bool = False,
    ) -> None:

        self.working_dir_temporary = False
        if path_or_url:
            if os.path.isdir(path_or_url):
                working_dir = working_dir or path_or_url
            elif not offline and self._is_url(path_or_url):
                git_url = git_url or path_or_url

        self.git_repo = git_repo
        self.working_dir = working_dir
        self._ref = ref
        self.git_project = git_project
        self.git_service = git_service
        self.git_url = git_url
        self.full_name = full_name
        self.repo_name = repo_name
        self.namespace = namespace

        change = True
        while change:
            # we are trying to get new information while it is possible
            # new iteration is done only if there was a change in the last iteration

            change = (
                self._parse_repo_name_full_name_and_namespace()
                or self._parse_git_repo_from_working_dir(offline=offline)
                or self._parse_git_project(offline)
                or self._parse_git_service(offline)
                or self._parse_ref_from_git_repo()
                or self._parse_working_dir()
                or self._parse_git_repo_from_git_url(offline)
                or self._parse_git_url(offline)
                or self._parse_repo_name_from_git_project()
                or self._parse_namespace_from_git_project()
                or self._parse_git_url_from_git_repo()
                or self._parse_namespace_from_git_repo()
            )

        if ref:
            # If ref was specified, we will checkout that

            if ref not in self.git_repo.branches:
                self.git_repo.create_head(self._ref)

            self.git_repo.branches[self._ref].checkout()

    @property
    def ref(self):
        """
        Name of the HEAD if the HEAD is not detached,
        else commit hash.
        """
        if self.git_repo:
            return self._get_ref_from_git_repo()
        return None

    def _is_url(self, path_or_url):
        try:
            res = requests.head(path_or_url)
            if res.ok:
                return True
            else:
                logger.warning("path_or_url is nor directory nor url")
        except requests.exceptions.BaseHTTPError:
            logger.warning("path_or_url is nor directory nor url")
        return False

    def _parse_namespace_from_git_repo(self):
        if self.git_repo and not self.namespace:
            self.namespace = get_namespace(self.git_url)
            if self.namespace:
                return True
        return False

    def _parse_git_url_from_git_repo(self):
        if self.git_repo and not self.git_url:
            # this is prone to errors
            # also if we want url to upstream, we may want to ask for it explicitly
            # since this can point to a fork
            # .urls returns generator
            self.git_url = list(self.git_repo.remote().urls)[0]
            logger.debug(f"remote url of the repo is {self.git_url}")
            return True
        return False

    def _parse_namespace_from_git_project(self):
        if self.git_project and not self.namespace:
            self.namespace = self.git_project.namespace
            return True
        return False

    def _parse_repo_name_from_git_project(self):
        if self.git_project and not self.repo_name:
            self.repo_name = self.git_project.repo
            return True
        return False

    def _parse_git_url(self, offline):
        if self.git_project and not self.git_url and not offline:
            self.git_url = self.git_project.get_git_urls()["git"]
            return True
        return False

    def _parse_git_repo_from_git_url(self, offline):
        if self.git_url and not self.working_dir and not self.git_repo and not offline:
            self.git_repo = get_repo(url=self.git_url)
            self.working_dir_temporary = True
            return True
        return False

    def _parse_working_dir(self):
        if self.git_repo and not self.working_dir:
            self.working_dir = self.git_repo.working_dir
            return True
        return False

    def _parse_ref_from_git_repo(self):
        if self.git_repo and not self._ref:
            self._ref = self._get_ref_from_git_repo()
            return self._ref is not None
        return False

    def _parse_git_service(self, offline):
        if self.git_project and not self.git_service and not offline:
            self.git_service = self.git_project.service
            return True
        return False

    def _parse_git_project(self, offline: bool) -> bool:

        if (
            self.repo_name
            and self.namespace
            and self.git_service
            and not self.git_project
            and not offline
        ):
            self.git_project = self.git_service.get_project(
                repo=self.repo_name, namespace=self.namespace
            )
            return True
        return False

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
        return change

    def _parse_git_repo_from_working_dir(self, offline: bool) -> bool:
        """
        Get the repo from the self.working_dir (clone self.git_url if it is not a git repo)
        """
        if self.working_dir and not self.git_repo:
            logger.debug("working_dir is set and git_repo is not: let's discover...")
            if is_git_repo(directory=self.working_dir):
                logger.debug("it's a git repo!")
                self.git_repo = git.Repo(path=self.working_dir)
                return True

            elif self.git_url and not offline:
                logger.debug(
                    "we just cloned git repo %s to %s", self.git_url, self.working_dir
                )
                self.git_repo = get_repo(url=self.git_url, directory=self.working_dir)
                return True

        return False

    def clean(self):
        if self.working_dir_temporary:
            logger.debug(f"Cleaning: {self.working_dir}")
            shutil.rmtree(self.working_dir)
            self.working_dir_temporary = False

    def _get_ref_from_git_repo(self):
        if self.git_repo.head.is_detached:
            return self.git_repo.head.commit.hexsha
        else:
            return self.git_repo.active_branch

    def __del__(self):
        self.clean()
