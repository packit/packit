#!/usr/bin/python3
"""
Watch for new pull requests and changes to existing pull requests.
"""
import logging

import click

from packit.bot_api import PackitBotAPI
from packit.config import pass_config

logger = logging.getLogger(__name__)


@click.command("watch-pr")
@click.argument("message-id", nargs=-1)
@pass_config
def watch_pr(config, message_id):
    """
    watch for activity on github and create/update a downstream PR

    :return: int, retcode
    """
    api = PackitBotAPI(config)
    if message_id:
        for msg_id in message_id:
            fedmsg_dict = api.consumerino.fetch_fedmsg_dict(msg_id)
            api.sync_upstream_pull_request_with_fedmsg(fedmsg_dict)
    else:
        api.watch_upstream_pull_request()
