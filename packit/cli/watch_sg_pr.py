#!/usr/bin/python3
"""
Watch for new pull requests and changes to existing pull requests.
"""
import logging

import click

from packit.api import PackitAPI


logger = logging.getLogger(__name__)


@click.command("watch-pr")
@click.argument("message-id", nargs=-1)
def watch_pr(message_id):
    """
    watch for activity on github and create/update a downstream PR

    :return: int, retcode
    """
    api = PackitAPI()
    if message_id:
        for msg_id in message_id:
            fedmsg_dict = api.fetch_fedmsg_dict(msg_id)
            api.sync_upstream_pr_to_distgit(fedmsg_dict)
    else:
        api.keep_syncing_upstream_pulls()
