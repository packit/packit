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
packit.utils.extensions
=======================

Keeps functions that extend Python collections (list to dict, get on nested dict)
and force strict evaluation (`assert_existence`).
"""

from typing import Any

from packit.exceptions import PackitException


def assert_existence(obj, name):
    """
    Force the lazy object to be evaluated.
    """
    if obj is None:
        raise PackitException(f"Object ({name}) needs to have a value.")


def nested_get(d: dict, *keys, default=None) -> Any:
    """
    recursively obtain value from nested dict

    :param d: dict
    :param keys: path within the structure
    :param default: a value to return by default

    :return: value or None
    """
    response = d
    for k in keys:
        try:
            response = response[k]
        except (KeyError, AttributeError, TypeError):
            # logger.debug("can't obtain %s: %s", k, ex)
            return default
    return response
