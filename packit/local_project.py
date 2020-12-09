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

import logging
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union, Iterable, Iterator

import git
from ogr import GitlabService
from ogr.abstract import GitProject, GitService
from ogr.parsing import parse_git_repo

from packit.exceptions import PackitException
from packit.utils.repo import is_git_repo, get_repo, is_a_git_ref

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
        working_dir: Union[Path, str] = None,
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
        self.git_repo: git.Repo = git_repo
        self.working_dir: Path = Path(working_dir) if working_dir else None
        self._ref = ref
        self.git_project = git_project
        self.git_service = git_service
        self.git_url = git_url
        self.full_name = full_name
        self.repo_name = repo_name
        self.namespace = namespace
        self.offline = offline
        self.remote = remote

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
        )

        if refresh:
            self.refresh_the_arguments()

        # p-s gives us both, commit hash for a PR and PR ID as well
        # since we want to have 'pr123' in the release field, let's check out
        # the PR itself, so if both are specified, PR ID > ref
        if pr_id:
            self.checkout_pr(pr_id)
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
    def ref(self) -> Optional[str]:
        """
        Name of the HEAD if the HEAD is not detached,
        else commit hash.
        """
        if self.git_repo:
            return self._get_ref_from_git_repo()
        return None

    @property
    def commit_hexsha(self) -> str:
        """
        Get the short commit hash for the current commit.

        :return: first 8 characters of the current commit
        """
        if self.git_repo.head.is_detached:
            return self.git_repo.head.commit.hexsha[:8]
        else:
            return self.git_repo.active_branch.commit.hexsha[:8]

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
                f"Leaving old ref {current_head!r} and checkout new ref {ref!r}"
            )
            if ref not in self.git_repo.refs:
                if not is_a_git_ref(self.git_repo, ref):
                    raise PackitException(
                        f"Git ref {ref!r} not found, cannot checkout."
                    )
                ref = self.git_repo.commit(ref).hexsha
            self.git_repo.git.checkout(ref)
        yield
        if ref:
            logger.debug(
                f"Leaving new ref {ref!r} and checkout old ref {current_head!r}"
            )
            self.git_repo.git.checkout(current_head)

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
                self.git_repo = git.Repo(path=self.working_dir)
                return True

            elif self.git_url and not self.offline:
                self.git_repo = get_repo(url=self.git_url, directory=self.working_dir)
                logger.debug(
                    f"We just cloned git repo {self.git_url} to {self.working_dir}."
                )
                return True

        return False

    def _parse_git_project_from_repo_namespace_and_git_project(
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
            self.git_repo = get_repo(url=self.git_url)
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

    def checkout_ref(self, ref: str):
        """ Check out selected ref in the git repo; equiv of git checkout -B ref """
        logger.info(f"Checking out ref {ref}.")
        if ref not in self.git_repo.branches:
            self.git_repo.create_head(self._ref)

        self.git_repo.branches[self._ref].checkout()

    def checkout_pr(self, pr_id: Union[str, int]):
        """
        Fetch selected PR and check it out.
        """
        is_gitlab = True if isinstance(self.git_service, GitlabService) else False
        logger.info(f"Checking out PR {pr_id}.")
        remote_name = self.remote or "origin"
        rem: git.Remote = self.git_repo.remotes[remote_name]
        remote_ref = "+refs/{}/{}/head".format(
            "merge-requests" if is_gitlab else "pull", pr_id
        )
        local_ref = f"refs/remotes/{remote_name}/pr/{pr_id}"
        local_branch = f"pr/{pr_id}"
        rem.fetch(f"{remote_ref}:{local_ref}")
        self.git_repo.create_head(local_branch, f"{remote_name}/{local_branch}")
        self.git_repo.branches[local_branch].checkout()

    def checkout_release(self, tag: str) -> None:
        logger.info(f"Checking out upstream version {tag}.")
        try:
            self.git_repo.git.checkout(tag)
        except Exception as ex:
            raise PackitException(f"Cannot checkout release tag: {ex!r}.")

    def push(
        self, refspec: str, remote_name: str = "origin", force: bool = False
    ) -> Iterable[git.PushInfo]:
        """
        push changes to a remote using provided refspec

        :param refspec: e.g. "master", "HEAD:f30"
        :param remote_name: name of the remote where we push
        :param force: force push: yes or no?
        :return: a list of git.remote.PushInfo objects - have fun
        """
        return self.git_repo.remote(name=remote_name).push(refspec=refspec, force=force)

    def stage(self, path: str = ".", force: bool = True):
        """
        stage provided path from working tree to index

        force: bypass gitignore
        """
        self.git_repo.git.add(path, force=force)

    def commit(
        self, message: str, body: Optional[str] = None, allow_empty: bool = True
    ):
        """ Commit staged changes """
        other_message_kwargs = {"message": body} if body else {}
        # some of the commits may be empty and it's not an error,
        # e.g. extra source files
        self.git_repo.git.commit(
            allow_empty=allow_empty, m=message, **other_message_kwargs
        )

    def get_commits(self, ref: str = "HEAD") -> Iterator[git.Commit]:
        return self.git_repo.iter_commits(ref)

    def fetch(self, remote: str, refspec: Optional[str] = None):
        """
        fetch refs from a remote to this repo

        @param remote: str or path of the repo we fetch from
        @param refspec: see man git-fetch
        """
        if refspec:
            self.git_repo.git.fetch(remote, refspec)
        else:
            self.git_repo.git.fetch(remote, "--tags")

    def rebase(self, ref: str):
        self.git_repo.git.rebase(ref)

    def reset(self, ref: str):
        """ git reset --hard $ref """
        self.git_repo.head.reset(ref, index=True, working_tree=True)

    def __del__(self):
        self.clean()
