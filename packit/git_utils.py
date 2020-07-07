# MIT License
#
# Copyright (c) 2020 Red Hat, Inc.

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
Helpers and wrappers on top of git.
"""
import logging
from typing import Optional

import git
import yaml

from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


def get_message_from_metadata(metadata: dict, header: Optional[str] = None) -> str:
    if not isinstance(metadata, dict):
        raise PackitException(
            f"We can save only dictionaries to metadata. Not {metadata}"
        )

    content = yaml.dump(metadata, indent=4) if metadata else ""
    if not header:
        return content

    return f"{header}\n\n{content}"


def get_metadata_from_message(commit: git.Commit) -> Optional[dict]:
    """
    Tries to load yaml format from the git message.

    We are skipping first line until
    the rest of the content is yaml-loaded to dictionary (yaml object type).

    If nothing found, we return None.

    Reference:
    https://gitpython.readthedocs.io/en/stable/reference.html
    ?highlight=archive#module-git.objects.commit

    e.g.:

    I)
    key: value
    another: value
    -> {"key": "value", "another": "value"}

    II)
    On sentence.

    key: value
    another: value
    -> {"key": "value", "another": "value"}

    III)
    A lot of
    text

    before keys.

    key: value
    another: value
    -> {"key": "value", "another": "value"}

    IV)
    Other values are supported as well:

    key:
    - first
    - second
    - third

    :param commit: git.Commit object
    :return: dict loaded from message if it satisfies the rules above
    """
    splitted_message = commit.message.split("\n")

    for i in range(len(splitted_message)):
        message_part = "\n".join(splitted_message[i:])
        try:
            loaded_part = yaml.safe_load(message_part)
        except yaml.YAMLError:
            continue

        if isinstance(loaded_part, dict):
            return loaded_part

    return None
