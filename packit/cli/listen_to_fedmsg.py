# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Watch for new upstream releases.
"""
import logging

import click

from packit.cli.utils import cover_packit_exception
from packit.config import pass_config
from packit.fed_mes_consume import Consumerino
from packit.jobs import SteveJobs

logger = logging.getLogger(__name__)


@click.command("listen-to-fedmsg")
@click.argument("message-id", nargs=-1)
@pass_config
@cover_packit_exception
def listen_to_fedmsg(config, message_id):
    """
    Listen to events on fedmsg and process them.

    if MESSAGE-ID is specified, process only the selected messages
    """

    consumerino = Consumerino()
    steve = SteveJobs(config)

    if message_id:
        for msg_id in message_id:
            fedmsg_dict = consumerino.fetch_fedmsg_dict(msg_id)
            steve.process_message(fedmsg_dict)
    else:
        for topic, msg in consumerino.yield_all_messages():
            steve.process_message(msg, topic=topic)
