import logging
from functools import lru_cache

from onegittorulethemall.services.abstract import GitService, GitProject
from onegittorulethemall.services.our_pagure import OurPagure

logger = logging.getLogger(__name__)


def replace_username_with_username(dictionary):
    result = dictionary.copy()
    if "username" in result and "fork_username" not in result:
        result["fork_username"] = result["username"]
        del (result["username"])
    return result


class PagureService(GitService):
    def __init__(
            self, token=None, instance_url="https://src.fedoraproject.org", **kwargs
    ):
        super().__init__()
        self.instance_url = instance_url
        self.token = token
        self.pagure_kwargs = kwargs

        self.pagure = OurPagure(
            pagure_token=token,
            instance_url=instance_url,
            **replace_username_with_username(kwargs),
        )

    def get_project(self, **kwargs):
        project_kwargs = self.pagure_kwargs.copy()
        project_kwargs.update(kwargs)
        return PagureProject(
            instance_url=self.instance_url, token=self.token, **project_kwargs
        )

    @property
    def token_username(self):
        return self.pagure.whoami()


class PagureProject(GitProject):
    def __init__(
            self,
            repo=None,
            namespace=None,
            username=None,
            instance_url=None,
            token=None,
            is_fork=False,
            **kwargs,
    ):
        super().__init__()
        self.repo = repo
        self.namespace = namespace
        self._username = username
        self.instance_url = instance_url
        self.token = token
        self._is_fork = is_fork or False
        self.pagure_kwargs = kwargs

        self.pagure = OurPagure(
            pagure_token=token,
            pagure_repository=f"{self.namespace}/{self.repo}",
            namespace=namespace,
            fork_username=username if is_fork else None,
            instance_url=instance_url,
            **kwargs,
        )

    @property
    @lru_cache()
    def username(self):
        return self._username or self.pagure.whoami()

    @property
    def branches(self):
        return self.pagure.branches

    @property
    def description(self):
        return self.pagure.project_description

    def pr_list(self, status="open"):
        return self.pagure.list_requests(status=status)

    def pr_comment(self, pr_id, body, commit=None, filename=None, row=None):
        return self.pagure.comment_request(
            request_id=pr_id, body=body, commit=commit, filename=filename, row=row
        )

    def pr_close(self, pr_id):
        return self.pagure.close_request(request_id=pr_id)

    def pr_info(self, pr_id):
        return self.pagure.request_info(request_id=pr_id)

    def pr_merge(self, pr_id):
        return self.pagure.merge_request(request_id=pr_id)

    def pr_create(self, title, body, target_branch, source_branch):
        return self.pagure.create_request(
            title=title,
            body=body,
            target_branch=target_branch,
            source_branch=source_branch,
        )

    def fork_create(self):
        return self.pagure.create_fork()

    @property
    def fork(self):
        """PagureRepo instance of the fork of this repo."""
        kwargs = replace_username_with_username(self.pagure_kwargs)
        kwargs.update(
            repo=self.repo,
            namespace=self.namespace,
            username=self.username,
            instance_url=self.instance_url,
            token=self.token,
            is_fork=True,
        )
        fork_project = PagureProject(**kwargs)
        try:
            if fork_project.exists and fork_project.pagure.parent:
                return fork_project
        except:
            return None
        return None

    @property
    def is_fork(self):
        return self._is_fork

    @property
    def exists(self):
        return self.pagure.project_exists

    @property
    def is_forked(self):
        return self.fork is not None

    @property
    def git_urls(self):
        return self.pagure.git_urls

    def get_commit_flags(self, commit):
        return self.pagure.get_commit_flags(commit=commit)
