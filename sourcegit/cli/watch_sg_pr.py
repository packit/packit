#!/usr/bin/python3
"""
Watch for new pull requests and changes to existing pull requests.
"""
import logging

import click

from sourcegit.api import SourceGitAPI


logger = logging.getLogger(__name__)


@click.command("watch-pr")
@click.argument("message-id", nargs=-1)
def watch_pr(message_id):
    """
    watch for activity on github and create/update a downstream PR

    :return: int, retcode
    """
    a = SourceGitAPI()
    if message_id:
        for msg_id in message_id:
            fedmsg_dict = a.fetch_fedmsg_dict(msg_id)
            a.sync_upstream_pr_to_distgit(fedmsg_dict)
    else:
        a.keep_syncing_upstream_pulls()
