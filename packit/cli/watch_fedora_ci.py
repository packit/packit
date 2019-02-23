"""
This bot will listen on fedmsg for finished CI runs and will update respective source gits
"""
import logging

import click

from packit.api import PackitAPI
from packit.config import get_context_settings


logger = logging.getLogger(__name__)


@click.command("watch-fedora-ci", context_settings=get_context_settings())
@click.argument("message_id", nargs=-1, required=False)
def watcher(message_id):
    """
    watch for flags on PRs: try to process those which we know mapping for

    :return: int, retcode
    """
    api = PackitAPI()

    if message_id:
        for msg_id in message_id:
            fedmsg_dict = api.fetch_fedmsg_dict(msg_id)
            api.process_ci_result(fedmsg_dict)
            return
    else:
        api.keep_fwding_ci_results()
