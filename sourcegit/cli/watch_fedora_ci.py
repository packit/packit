"""
This bot will listen on fedmsg for finished CI runs and will update respective source gits
"""
import logging

import click
import fedmsg

from sourcegit.api import SourceGitAPI
from sourcegit.config import get_context_settings


package_mapping = {
    "python-docker": {
        "source-git": "TomasTomecek/docker-py-source-git"
    }
}

logger = logging.getLogger(__name__)


@click.command("watch-fedora-ci", context_settings=get_context_settings())
@click.argument("message_id", nargs=-1, required=False)
def watcher(message_id):
    """
    watch for flags on PRs: try to process those which we know mapping for

    :return: int, retcode
    """
    # we can watch for runs directly:
    # "org.centos.prod.ci.pipeline.allpackages.complete"
    topic = "org.fedoraproject.prod.pagure.pull-request.flag.added"

    a = SourceGitAPI()

    if message_id:
        for msg_id in message_id:
            fedmsg_dict = a.fetch_fedmsg_dict(msg_id)
            a.process_ci_result(fedmsg_dict)
            return
    else:
        logger.info("listening on fedmsg, topic=%s", topic)
        for name, endpoint, topic, msg in fedmsg.tail_messages(topic=topic):
            a.process_ci_result(msg)
