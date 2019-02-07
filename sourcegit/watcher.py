"""
Watch CI and report results back to upstream.
"""
import logging

import github

from ogr.services.pagure import PagureService
from sourcegit.downstream_checks import DownstreamCheck

logger = logging.getLogger(__name__)


class SourceGitCheckHelper:
    """
    This class provides functionality to operate on github pull request checks
    """

    def __init__(self, github_token, pagure_user_token):
        self.pagure_token = pagure_user_token
        self.github_token = github_token
        self.gh = github.Github(login_or_token=self.github_token)

    def set_init_check(self, full_name: str, pr_id: int, check: DownstreamCheck):
        """
        Reset status for the selected check to the init state

        :param full_name: str, name of the github repo
        :param pr_id: str, ID of the github pull request
        :param check instance of DownstreamCheck
        :return:
        """

        repo = self.gh.get_repo(full_name)
        sg_pull = repo.get_pull(pr_id)
        top_commit = list(sg_pull.get_commits())[-1]

        top_commit.create_status(
            check.status,
            target_url=check.url,
            description=check.description,
            context=check.name,
        )

    # TODO: split this method: fedmsg parsing vs. the actual work
    def process_new_dg_flag(self, msg):
        """
        Process flags from the PR and update source git PR with those flags
        :param msg:
        :return:
        """
        project_name = msg["msg"]["pullrequest"]["project"]["name"]
        logger.info("new flag for PR for %s", project_name)

        try:
            source_git = get_package_mapping()[project_name]["source-git"]
        except KeyError:
            logger.info("source git not found")
            return

        ps = PagureService(token=self.pagure_token)
        project = ps.get_project(repo=project_name, namespace="rpms")

        pr_id = msg["msg"]["pullrequest"]["id"]

        # find info for the matching source git pr
        sg_pr_id = project.get_sg_pr_id(pr_id)

        # check the commit which tests were running for
        commit = project.get_sg_top_commit(pr_id)

        if not (sg_pr_id and commit):
            logger.info("this doesn't seem to be a source-git related event")
            return

        repo = self.gh.get_repo(source_git)
        sg_pull = repo.get_pull(sg_pr_id)
        for c in sg_pull.get_commits():
            if c.sha == commit:
                gh_commit = c
                break
        else:
            raise RuntimeError("commit was not found in source git")

        # Pagure states match github states, coolzies
        # https://developer.github.com/v3/repos/statuses/#create-a-status
        gh_commit.create_status(
            msg["msg"]["flag"]["status"],
            target_url=msg["msg"]["flag"]["url"],
            description=msg["msg"]["flag"]["comment"],
            context=msg["msg"]["flag"]["username"],  # simple-koji-ci or Fedora CI
        )
