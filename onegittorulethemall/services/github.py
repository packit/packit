import json
import logging
import re

import github
import time

from .abstract import GitService
from ..utils import (clone_repo_and_cd_inside, fetch_all, get_commit_msgs,
                     prompt_for_pr_content, set_origin_remote,
                     set_upstream_remote, git_push)

logger = logging.getLogger(__name__)


def get_github_full_name(repo_url):
    """ convert remote url into a <owner>/<repo> """
    s = re.sub(r"^[a-zA-Z0-9:/@]+?github.com.", "", repo_url)
    return re.sub(r"\.git$", "", s)


class GithubService(GitService):
    name = "github"

    def __init__(self, token=None, full_repo_name=None):
        super().__init__(token=token)

        self.g = github.Github(login_or_token=self.token)
        self.user = self.g.get_user()
        self.repo = None
        if full_repo_name:
            self.repo = self.g.get_repo(full_repo_name)

    @classmethod
    def create_from_remote_url(cls, remote_url, **kwargs):
        """ create instance of service from provided remote_url """
        if "github.com" not in remote_url:
            return None
        full_repo_name = get_github_full_name(remote_url)
        logger.debug("github repo name: %s", full_repo_name)
        return cls(full_repo_name=full_repo_name, **kwargs)

    @staticmethod
    def is_fork_of(user_repo, target_repo):
        """ is provided repo fork of gh.com/{parent_repo}/? """
        return user_repo.create_fork and user_repo.parent and \
               user_repo.parent.full_name == target_repo

    def create_fork(self, target_repo):

        target_repo_org, target_repo_name = target_repo.split("/", 1)

        target_repo_gh = self.g.get_repo(target_repo)

        try:
            # is it already forked?
            user_repo = self.user.get_repo(target_repo_name)
            if not self.is_fork_of(user_repo, target_repo):
                raise RuntimeError("repo %s is not a fork of %s" % (user_repo, target_repo_gh))
        except github.UnknownObjectException:
            # nope
            user_repo = None

        if self.user.login == target_repo_org:
            # user wants to fork its own repo; let's just set up remotes 'n stuff
            if not user_repo:
                raise RuntimeError("repo %s not found" % target_repo_name)
            clone_repo_and_cd_inside(user_repo.name, user_repo.ssh_url, target_repo_org)
        else:
            user_repo = self._fork_gracefully(target_repo_gh)

            clone_repo_and_cd_inside(user_repo.name, user_repo.ssh_url, target_repo_org)

            set_upstream_remote(clone_url=target_repo_gh.clone_url,
                                ssh_url=target_repo_gh.ssh_url,
                                pull_merge_name="pull")
        set_origin_remote(user_repo.ssh_url, pull_merge_name="pull")
        fetch_all()

    def _fork_gracefully(self, target_repo):
        """ fork if not forked, return forked repo """
        try:
            target_repo.full_name
        except github.GithubException.UnknownObjectException:
            logger.error("repository doesn't exist")
            raise RuntimeError("repo %s not found" % target_repo)
        logger.info("forking repo %s", target_repo)
        return self.user.create_fork(target_repo)

    def pr_create(self, target_remote, target_branch, current_branch):
        """
        create pull request on repo specified in target_remote against target_branch
        from current_branch

        :param target_remote: str, git remote to create PR against
        :param target_branch: str, git branch to create PR against
        :param current_branch: str, local branch with the changes
        :return: URL to the PR
        """
        head = "{}:{}".format(self.user.login, current_branch)
        logger.debug("PR head is: %s", head)

        base = "{}/{}".format(target_remote, target_branch)

        git_push()

        title, body = prompt_for_pr_content(get_commit_msgs(base))

        opts = {
            "title": title,
            "body": body,
            "base": target_branch,
            "head": head,
        }
        logger.debug("PR to be created: %s", json.dumps(opts, indent=2))
        # TODO: configurable, prompt instead maybe?
        time.sleep(4.0)
        pr = self.repo.create_pull(**opts)
        logger.info("PR link: %s", pr.html_url)
        return pr.html_url

    def pr_list(self):
        """
        Get list of pull-requests for the repository.

        :return: [PullRequest]
        """
        prs = self.repo.get_pulls(state="open",
                                  sort="updated",
                                  direction="desc")
        return [
            {
                'id': pr.number,
                'title': pr.title,
                'author': pr.user.login,
                'url': pr.html_url,
            }
            for pr in prs]

    def list_labels(self):
        """
        Get list of labels in the repository.
        :return: [Label]
        """
        return list(self.repo.get_labels())

    def update_labels(self, labels):
        """
        Update the labels of the repository. (No deletion, only add not existing ones.)

        :param labels: [str]
        :return: int - number of added labels
        """
        current_label_names = [l.name for l in list(self.repo.get_labels())]
        changes = 0
        for label in labels:
            if label.name not in current_label_names:
                color = self._normalize_label_color(color=label.color)
                self.repo.create_label(name=label.name,
                                       color=color,
                                       description=label.description or "")

                changes += 1
        return changes

    @staticmethod
    def _normalize_label_color(color):
        if color.startswith('#'):
            return color[1:]
        return color
