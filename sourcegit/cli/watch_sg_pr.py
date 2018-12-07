#!/usr/bin/python3
"""
Watch for new pull requests and changes to existing pull requests.
"""
import logging
import sys

import click
import fedmsg
import requests

from sourcegit.config import pass_config
from sourcegit.sync import Synchronizer

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
    pr_action = 'updated' if updated else 'open'
    topic = f"org.fedoraproject.prod.github.pull_request.{pr_action}"

    with Synchronizer() as sync:
        if message_id:
            for msg_id in message_id:
                logger.debug(f"Proccessing message: {msg_id}")
                url = f"https://apps.fedoraproject.org/datagrepper/id?id={msg_id}&is_raw=true"
                response = requests.get(url)
                dest_dir = sync.sync_using_fedmsg_dict(response.json())
                logger.info(dest_dir)
            sys.exit(0)

        for name, endpoint, topic, msg in fedmsg.tail_messages(topic=topic):
            logger.debug(f"Proccessing message: {msg}")
            dest_dir = sync.sync_using_fedmsg_dict(msg)
            logger.info(dest_dir)
