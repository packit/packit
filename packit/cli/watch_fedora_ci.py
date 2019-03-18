"""
This bot will listen on fedmsg for finished CI runs and will update respective source gits
"""
import logging

import click

from packit.api import PackitAPI
from packit.cli.utils import cover_packit_exception
from packit.config import get_context_settings, pass_config

logger = logging.getLogger(__name__)


@click.command("watch-fedora-ci", context_settings=get_context_settings())
@click.argument("message_id", nargs=-1, required=False)
@pass_config
@cover_packit_exception
def watcher(config, message_id):
    """
    Watch for flags on PRs: try to process those which we know mapping for

    :return: int, retcode
    """
    api = PackitAPI(config)

    if message_id:
        for msg_id in message_id:
            fedmsg_dict = api.fetch_fedmsg_dict(msg_id)
            api.process_ci_result(fedmsg_dict)
            return
    else:
        api.keep_fwding_ci_results()
