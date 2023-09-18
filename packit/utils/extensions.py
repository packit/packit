# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

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
    try:
        for k in keys:
            response = response[k]
    except (KeyError, AttributeError, TypeError):
        # logger.debug("can't obtain %s: %s", k, ex)
        return default
    return response
