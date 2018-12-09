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
    pr_action = 'synchronize' if updated else 'opened'
    # pr_action == action from the payload
    # https://developer.github.com/v3/activity/events/types/#events-api-payload-28
    # https://github.com/fedora-infra/github2fedmsg/blob/a9c178b93aa6890e6b050e5f1c5e3297ceca463c/github2fedmsg/views/webhooks.py#L120
    topic = f"org.fedoraproject.prod.github.pull_request.{pr_action}"

    with Synchronizer() as sync:
        if message_id:
            # curl 'https://apps.fedoraproject.org/datagrepper/raw?category=github&user=ttomecek'
            # curl -s 'https://apps.fedoraproject.org/datagrepper/raw?topic=org.fedoraproject.prod.github.pull_request.synchronize&user=ttomecek' | jq
            # 2018-224ea166-7aaa-4e20-a932-514bef665b1e
            for msg_id in message_id:
                logger.debug(f"Proccessing message: {msg_id}")
                url = f"https://apps.fedoraproject.org/datagrepper/id?id={msg_id}&is_raw=true"
                response = requests.get(url)
                msg_dict = response.json()
                dest_dir = sync.sync_using_fedmsg_dict(msg_dict)
                logger.info(dest_dir)
            sys.exit(0)

        for name, endpoint, topic, msg in fedmsg.tail_messages(topic=topic):
            logger.debug(f"Proccessing message: {msg}")
            dest_dir = sync.sync_using_fedmsg_dict(msg)
            logger.debug("destination dir = %s", dest_dir)
