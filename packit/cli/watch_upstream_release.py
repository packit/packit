"""
Watch for new upstream releases.
"""
import logging

import click

from packit.bot_api import PackitBotAPI
from packit.cli.utils import cover_packit_exception
from packit.config import pass_config


logger = logging.getLogger(__name__)


@click.command("watch-releases")
@click.argument("message-id", nargs=-1)
@pass_config
@cover_packit_exception
def watch_releases(config, message_id):
    """
    Watch for activity on github and for every new upstream release, create a
    downstream pull request

    if MESSAGE-ID is specified, process only the selected fedmsg
    """
    api = PackitBotAPI(config)
    if message_id:
        for msg_id in message_id:
            fedmsg_dict = api.consumerino.fetch_fedmsg_dict(msg_id)
            api.sync_upstream_release_with_fedmsg(fedmsg_dict)
    else:
        api.watch_upstream_release()
