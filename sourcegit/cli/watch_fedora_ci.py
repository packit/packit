"""
This bot will listen on fedmsg for finished CI runs and will update respective source gits
"""

import os
import re

import click
import fedmsg
import libpagure
import github
import requests

from sourcegit.config import get_context_settings

package_mapping = {
    "python-docker": {
        "source-git": "TomasTomecek/docker-py-source-git"
    }
}


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
        pagure = libpagure.Pagure(
            pagure_token=self.pagure_token,
            pagure_repository=msg["msg"]["pullrequest"]["project"]["fullname"],
            instance_url="https://src.fedoraproject.org/"
        )
        try:
            project_name = msg["msg"]["pullrequest"]["project"]["name"]
            print(project_name)
            source_git = package_mapping[project_name]["source-git"]
        except KeyError:
            print("invalid message format or source git not found")
            return
        pr_id = msg["msg"]["pullrequest"]["id"]
        pr_info = pagure.request_info(pr_id)
        pr_description = pr_info["initial_comment"]

        # find info for the matching source git pr
        re_search = re.search(r"Source-git pull request ID:\s*(\d+)", pr_description)
        try:
            sg_pr_id = int(re_search[1])
        except (IndexError, ValueError):
            print("Source git PR not found")
            return

        # check the commit which tests were running for
        re_search = re.search(r"Source-git commit:\s*(\w+)", pr_description)
        try:
            commit = re_search[1]
        except (IndexError, ValueError):
            print("Source git commit not found")
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
    import ipdb; ipdb.set_trace()

    h = Holyrood()

    if message_id:
        url = f"https://apps.fedoraproject.org/datagrepper/id?id={message_id}&is_raw=true"
        response = requests.get(url)
        h.process_pr(response.json())
        return 0

    print(f"Listening on fedmsg, topic={topic}")

    for name, endpoint, topic, msg in fedmsg.tail_messages(topic=topic):
        h.process_pr(msg)
    return 0
