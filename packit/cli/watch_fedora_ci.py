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
