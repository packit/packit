#!/usr/bin/python3
"""
Watch for new pull requests and changes to existing pull requests.
"""
import logging

import click
import fedmsg

from sourcegit.api import SourceGitAPI
from sourcegit.config import pass_config

logger = logging.getLogger(__name__)


@click.command("watch-pr")
@click.option("--updated", is_flag=True, help="Watch PRs for update.")
@click.argument("message-id", nargs=-1)
@pass_config
def watch_pr(config, updated, message_id):
    """
    watch for activity on github and create/update a downstream PR

    :return: int, retcode
    """
    pr_action = 'synchronize' if updated else 'opened'
    # pr_action == action from the payload
    # https://developer.github.com/v3/activity/events/types/#events-api-payload-28
    # https://github.com/fedora-infra/github2fedmsg/blob/a9c178b93aa6890e6b050e5f1c5e3297ceca463c/github2fedmsg/views/webhooks.py#L120
    topic = f"org.fedoraproject.prod.github.pull_request.{pr_action}"

    a = SourceGitAPI()

    if message_id:
        for msg_id in message_id:
            fedmsg_dict = a.fetch_fedmsg_dict(msg_id)
            a.sync_upstream_pr_to_distgit(fedmsg_dict)
    else:
        logger.info("listening on fedmsg, topic=%s", topic)
        for name, endpoint, topic, msg in fedmsg.tail_messages(topic=topic):
            dest_dir = a.sync_upstream_pr_to_distgit(msg)
            logger.debug("destination dir = %s", dest_dir)
