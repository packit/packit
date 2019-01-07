import logging
import re
from functools import lru_cache

from onegittorulethemall.services.abstract import GitService, GitProject
from onegittorulethemall.services.our_pagure import OurPagure
from sourcegit.constants import dg_pr_key_sg_pr, dg_pr_key_sg_commit

logger = logging.getLogger(__name__)


def sanitize_fork_username(dictionary):
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
            **sanitize_fork_username(kwargs),
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
        self.forked_project = None

        self.pagure = OurPagure(
            pagure_token=token,
            pagure_repository=f"{self.namespace}/{self.repo}",
            namespace=namespace,
            fork_username=username if is_fork else None,
            instance_url=instance_url,
            **kwargs,
        )

    def __str__(self):
        return f"namespace={self.namespace} repo={self.repo} username={self.username}"

    def __repr__(self):
        return f"PagureProject(namespace={self.namespace}, repo={self.repo}, username={self.username})"

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

    def pr_list(self, status="Open"):
        return self.pagure.list_requests(status=status)

    def pr_comment(self, pr_id, body, commit=None, filename=None, row=None):
        return self.pagure.comment_request(
            request_id=pr_id, body=body, commit=commit, filename=filename, row=row
        )

    def pr_close(self, pr_id):
        return self.pagure.close_request(request_id=pr_id)

    def pr_info(self, pr_id):
        return self.pagure.request_info(request_id=pr_id)

    def search_in_pr_comments(self, pr_id, regex, pr_info=None):
        """
        Use re.search using the given regex on PR comments, default to PR description

        :param pr_id: str, ID of the pull request
        :param regex: str, regular expression
        :param pr_info, dict, existing pr_info dict = optimization and saving queries
        :return: return value of re.search
        """
        r = re.compile(regex)
        pr_info = pr_info or self.pr_info(pr_id)
        pr_comments = pr_info["comments"]
        # let's start with the recent ones first
        pr_comments = reversed(pr_comments)
        pr_description = pr_info["initial_comment"]
        for c in pr_comments:
            out = r.search(c["comment"])
            if out:
                return out
        return r.search(pr_description)

    def get_sg_top_commit(self, pr_id, pr_info=None):
        """
        Find source-git top commit ID in description of the selected dist-git pull request

        :param pr_id: str, ID of the pull request
        :param pr_info, dict, existing pr_info dict = optimization and saving queries
        :return: int or None
        """
        re_search = self.search_in_pr_comments(pr_id, r"%s:\s*(\w+)" % dg_pr_key_sg_commit, pr_info=pr_info)
        try:
            return re_search[1]
        except (IndexError, ValueError):
            logger.error("source git commit not found")
            return

    def get_sg_pr_id(self, pr_id, pr_info=None):
        """
        Find source-git PR ID in description of the selected dist-git pull request

        :param pr_id: str, ID of the pull request
        :param pr_info, dict, existing pr_info dict = optimization and saving queries
        :return: int or None
        """
        re_search = self.search_in_pr_comments(pr_id, r"%s:\s*(\d+)" % dg_pr_key_sg_pr, pr_info=pr_info)
        try:
            return int(re_search[1])
        except (IndexError, ValueError):
            logger.info("source git PR not found")
            return

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
        if self.forked_project is None:
            kwargs = sanitize_fork_username(self.pagure_kwargs)
            kwargs.update(
                repo=self.repo,
                namespace=self.namespace,
                username=self.username,
                instance_url=self.instance_url,
                token=self.token,
                is_fork=True,
            )
            self.forked_project = PagureProject(**kwargs)
            try:
                # why do we do this harakiri?
                if not (self.forked_project.exists and
                        self.forked_project.pagure.parent):
                    self.forked_project = None
            except Exception as ex:
                logger.info("exception while getting the forked project: %s", ex)
                self.forked_project = None
        return self.forked_project

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
