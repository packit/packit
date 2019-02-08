import logging
import shutil

import git

from ogr.abstract import GitProject, GitService
from packit.utils import is_git_repo, get_repo

logger = logging.getLogger(__name__)


class ClonedProject:
    def __init__(
            self,
            git_repo: git.Repo = None,
            working_dir: str = None,
            branch: str = None,
            git_project: GitProject = None,
            git_service: GitService = None,
            git_url: str = None,
            full_name: str = None,
            namespace: str = None,
            repo_name: str = None,
    ) -> None:

        self.git_repo = git_repo
        self.working_dir = working_dir
        self._branch = branch
        self.git_project = git_project
        self.git_service = git_service
        self.git_url = git_url
        self.full_name = full_name
        self.repo_name = repo_name
        self.namespace = namespace
        self.working_dir_created = False

        change = True
        while change:
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

            if (
                    self.repo_name
                    and self.namespace
                    and self.git_service
                    and not self.git_project
            ):
                self.git_project = self.git_service.get_project(
                    repo=self.repo_name, namespace=self.namespace
                )
                change = True

            if self.git_project and not self.git_service:
                self.git_service = self.git_project.service
                change = True

            if self.git_repo and not self._branch:
                self._branch = self.git_repo.active_branch
                change = True

            if self.git_repo and not self.working_dir:
                self.working_dir = self.git_repo.working_dir
                change = True

            if self.working_dir and not self.git_repo:
                if is_git_repo(self.working_dir):
                    self.git_repo = git.Repo(path=self.working_dir)
                    change = True
                elif self.git_url:
                    self.git_repo = get_repo(
                        url=self.git_url, directory=self.working_dir
                    )
                    change = True

            if self.git_url and not self.working_dir and not self.git_repo:
                self.git_repo = get_repo(url=self.git_url)
                self.working_dir_created = True
                change = True

            if self.git_project and not self.git_url:
                self.git_url = self.git_project.get_git_urls()["git"]
                change = True

            if self.git_project and not self.repo_name:
                self.repo_name = self.git_project.repo
                change = True

            if self.git_project and not self.namespace:
                self.namespace = self.git_project.namespace
                change = True

            if self.git_repo and not self.git_url:
                self.git_url = self.git_repo.remote().urls[0]
                change = True

        if branch:

            if branch not in self.git_repo.branches:
                self.git_repo.create_head(self._branch)

            self.git_repo.branches[self._branch].checkout()

    def clean(self):
        if self.working_dir_created:
            logger.debug(f"Cleaning: {self.working_dir}")
            shutil.rmtree(self.working_dir)
            self.working_dir_created = False

    @property
    def branch(self):
        if self.git_repo:
            return self.git_repo.active_branch
        return None

    def __del__(self):
        self.clean()
