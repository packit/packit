"""
This bot will listen on fedmsg for finished CI runs and will update respective source gits
"""
import logging
import os

import click
import fedmsg
import github
import requests

from onegittorulethemall.services.pagure import PagureService
from sourcegit.config import get_context_settings


package_mapping = {
    "python-docker": {
        "source-git": "TomasTomecek/docker-py-source-git"
    }
}

logger = logging.getLogger(__name__)


class Holyrood:
    """ such a good gin """

    def __init__(self):
        self.pagure_token = os.environ["PAGURE_TOKEN"]
        self.github_token = os.environ["GITHUB_TOKEN"]
        self.g = github.Github(login_or_token=self.github_token)

    def process_pr(self, msg):
        """
        Process flags from the PR and update source git PR with those flags
        :param msg:
        :return:
        """
        project_name = msg["msg"]["pullrequest"]["project"]["name"]

        ps = PagureService(token=self.pagure_token)
        project = ps.get_project(repo=project_name, namespace="rpms")

        try:
            logger.info("new flag for PR for %s", project_name)
            source_git = package_mapping[project_name]["source-git"]
        except KeyError:
            logger.info("source git not found")
            return
        pr_id = msg["msg"]["pullrequest"]["id"]

        # find info for the matching source git pr
        sg_pr_id = project.get_sg_pr_id(pr_id)

        # check the commit which tests were running for
        commit = project.get_sg_top_commit(pr_id)

        if not (sg_pr_id and commit):
            logger.info("this doesn't seem to be a source-git related event")
            return

        repo = self.g.get_repo(source_git)
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


@click.command("watch-fedora-ci", context_settings=get_context_settings())
@click.argument("message_id", required=False)
def watcher(message_id):
    """
    watch for flags on PRs: try to process those which we know mapping for

    :return: int, retcode
    """
    # we can watch for runs directly:
    # "org.centos.prod.ci.pipeline.allpackages.complete"
    topic = "org.fedoraproject.prod.pagure.pull-request.flag.added"

    h = Holyrood()

    if message_id:
        url = f"https://apps.fedoraproject.org/datagrepper/id?id={message_id}&is_raw=true"
        response = requests.get(url)
        h.process_pr(response.json())
        return 0

    logger.info("listening on fedmsg, topic=%s", topic)

    for name, endpoint, topic, msg in fedmsg.tail_messages(topic=topic):
        h.process_pr(msg)
    return 0
