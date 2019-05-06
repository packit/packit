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
import shutil
from contextlib import contextmanager
from typing import Optional, Union

import git

from urllib.parse import urlparse
from ogr.abstract import GitProject, GitService
from packit.exceptions import PackitException

from packit.utils import (
    is_git_repo,
    get_repo,
    get_namespace_and_repo_name,
    is_a_git_ref,
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
    - path_or_url: working_dir if the directory exists
                    and git_url if the request is valid


    Local project can compute other attributes if it is possible.
    """

    # setting defaults to str because `None == ""` results into TypeError is not true-true
    def __init__(
        self,
        git_repo: git.Repo = None,
        working_dir: str = "",
        ref: str = "",
        git_project: GitProject = None,
        git_service: GitService = None,
        git_url: str = "",
        full_name: str = "",
        namespace: str = "",
        repo_name: str = "",
        path_or_url: str = "",
        offline: bool = False,
        refresh: bool = True,
        remote: str = "",
        pr_id: Optional[str] = None,
    ) -> None:
        """

        :param git_repo: git.Repo
        :param working_dir: str (working directory for the project)
        :param ref: str (git ref (branch/tag/commit) if set, then checkouted)
        :param git_project: ogr.GitProject (remote API for project)
        :param git_service: ogr.GitService (tokens for remote API)
        :param git_url: str (remote url used for cloning)
        :param full_name: str ("$namespace/$repo")
        :param namespace: str (namespace of the remote project)
        :param repo_name: str (name of the remote project)
        :param path_or_url: str (used as working_dir if it is an existing directory,
                                used as git_url if the it is a request-able url)
        :param offline: bool (do not use any network action, defaults to False)
        :param refresh: bool (calculate the missing attributes, defaults to True)
        :param remote: name of the git remote to use
        :param pr_id: ID of the pull request to fetch and check out
        """
        self.working_dir_temporary = False
        if path_or_url:
            if os.path.isdir(path_or_url):
                working_dir = working_dir or path_or_url
            elif not offline and self._is_url(path_or_url):
                git_url = git_url or path_or_url

        self.git_repo: git.Repo = git_repo
        self.working_dir: str = working_dir
        self._ref = ref
        self.git_project = git_project
        self.git_service = git_service
        self.git_url = git_url
        self.full_name = full_name
        self.repo_name = repo_name
        self.namespace = namespace
        self.offline = offline
        self.remote = remote

        if refresh:
            self.refresh_the_arguments()

        if ref:
            self.checkout_ref(ref)
        if pr_id:
            self.checkout_pr(pr_id)

    @property
    def ref(self) -> Optional[str]:
        """
        Name of the HEAD if the HEAD is not detached,
        else commit hash.
        """
        if self.git_repo:
            return self._get_ref_from_git_repo()
        return None

    def clean(self):
        if self.working_dir_temporary:
            logger.debug(f"Cleaning: {self.working_dir}")
            shutil.rmtree(self.working_dir)
            self.working_dir_temporary = False

    def refresh_the_arguments(self):
        change = True
        while change:
            # we are trying to get new information while it is possible
            # new iteration is done only if there was a change in the last iteration

            change = (
                self._parse_repo_name_full_name_and_namespace()
                or self._parse_git_repo_from_working_dir()
                or self._parse_git_project_from_repo_namespace_and_git_project()
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

    @contextmanager
    def git_checkout_block(self, ref: str = None):
        """Allows temporarily checkout another git-ref."""
        current_head = self._get_ref_from_git_repo()
        if ref:
            logger.debug(
                f"Leaving old ref: '{current_head}' and checkout new ref: '{ref}'"
            )
            if ref not in self.git_repo.refs:
                if not is_a_git_ref(self.git_repo, ref):
                    raise PackitException(
                        f"Git ref '{ref}' not found, cannot checkout."
                    )
                ref = self.git_repo.commit(ref).hexsha
            self.git_repo.git.checkout(ref)
        yield
        if ref:
            logger.debug(
                f"Leaving new ref: '{ref}' and checkout old ref: '{current_head}'"
            )
            self.git_repo.git.checkout(current_head)

    def _is_url(self, path_or_url):
        if urlparse(path_or_url).scheme:
            url = urlparse(path_or_url)
            logger.debug(f"Url {path_or_url} parsed. Resulting scheme: {url.scheme}")
            return True
        elif path_or_url.startswith("git@"):
            url = urlparse(
                path_or_url.replace(":", "/", 1).replace("git@", "git+ssh://", 1)
            )
            logger.debug(f"SSH style url {path_or_url} found.")
            logger.debug(
                f"Url parsed after replacing with {url.geturl()}. Resulting scheme: {url.scheme}"
            )
            return True
        logger.warning("path_or_url is nor directory nor url")
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

    def _parse_git_repo_from_working_dir(self) -> bool:
        """
        Get the repo from the self.working_dir (clone self.git_url if it is not a git repo)
        """
        if self.working_dir and not self.git_repo:
            logger.debug("working_dir is set and git_repo is not: let's discover...")
            if is_git_repo(directory=self.working_dir):
                logger.debug("it's a git repo!")
                self.git_repo = git.Repo(path=self.working_dir)
                return True

            elif self.git_url and not self.offline:
                logger.debug(
                    "we just cloned git repo %s to %s", self.git_url, self.working_dir
                )
                self.git_repo = get_repo(url=self.git_url, directory=self.working_dir)
                return True

        return False

    def _parse_git_project_from_repo_namespace_and_git_project(self,) -> bool:

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
            return True
        return False

    def _parse_git_service_from_git_project(self):
        if self.git_project and not self.git_service and not self.offline:
            self.git_service = self.git_project.service
            return True
        return False

    def _parse_ref_from_git_repo(self):
        if self.git_repo and not self._ref:
            self._ref = self._get_ref_from_git_repo()
            return bool(self._ref)
        return False

    def _parse_working_dir_from_git_repo(self):
        if self.git_repo and not self.working_dir:
            self.working_dir = self.git_repo.working_dir
            return True
        return False

    def _parse_git_repo_from_git_url(self):
        if (
            self.git_url
            and not self.working_dir
            and not self.git_repo
            and not self.offline
        ):
            self.git_repo = get_repo(url=self.git_url)
            self.working_dir_temporary = True
            return True
        return False

    def _parse_git_url_from_git_project(self):
        if self.git_project and not self.git_url and not self.offline:
            self.git_url = self.git_project.get_git_urls()["git"]
            return True
        return False

    def _parse_repo_name_from_git_project(self):
        if self.git_project and not self.repo_name:
            self.repo_name = self.git_project.repo
            if not self.repo_name:
                raise PackitException(
                    "Repo name should have been set but isn't, this is bug!"
                )
            return True
        return False

    def _parse_namespace_from_git_project(self):
        if self.git_project and not self.namespace:
            self.namespace = self.git_project.namespace
            return True
        return False

    def _parse_git_url_from_git_repo(self):
        if self.git_repo and not self.git_url:
            old_git_url = self.git_url
            if self.remote:
                self.git_url = next(self.git_repo.remote(self.remote).urls)
            else:
                # TODO: let's just default to origin
                self.git_url = next(self.git_repo.remote().urls)
            logger.debug(f"remote url of the repo is {self.git_url}")
            # trigger refresh if they are different
            return not (bool(old_git_url) == bool(self.git_url))
        return False

    def _parse_namespace_from_git_url(self):
        if self.git_url and (not self.namespace or not self.repo_name):
            namespace, repo_name = get_namespace_and_repo_name(self.git_url)
            if namespace == self.namespace and repo_name == self.repo_name:
                return False
            self.namespace, self.repo_name = namespace, repo_name
            logger.debug(
                f"Parsed namespace and repo name from url: {self.namespace}/{self.repo_name}"
            )
            return True
        return False

    def _get_ref_from_git_repo(self) -> str:
        if self.git_repo.head.is_detached:
            return self.git_repo.head.commit.hexsha
        else:
            return self.git_repo.active_branch.name

    def checkout_ref(self, ref: str):
        """ Check out selected ref in the git repo; equiv of git checkout -B ref """
        if ref not in self.git_repo.branches:
            self.git_repo.create_head(self._ref)

        self.git_repo.branches[self._ref].checkout()

    def checkout_pr(self, pr_id: Union[str, int]):
        """
        Fetch selected PR and check it out. This will work for github and pagure, not for gitlab.
        """
        logger.info(f"Checking out PR {pr_id}")
        remote_name = self.remote or "origin"
        rem: git.Remote = self.git_repo.remotes[remote_name]
        remote_ref = f"+refs/pull/{pr_id}/head"
        local_ref = f"refs/remotes/{remote_name}/pr/{pr_id}"
        local_branch = f"pr/{pr_id}"
        rem.fetch(f"{remote_ref}:{local_ref}")
        self.git_repo.create_head(local_branch, f"{remote_name}/{local_branch}")
        self.git_repo.branches[local_branch].checkout()

    def __del__(self):
        self.clean()
