# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from packaging.version import InvalidVersion, parse


def compare_versions(a: str, b: str) -> int:
    """
    Parses and compares two versions.

    Args:
        a: Version A.
        b: Version B.

    Returns:
        Positive number if A > B, negative number if A < B, zero if they are equal.
    """
    try:
        v_a = parse(a)
    except InvalidVersion:
        v_a = None
    try:
        v_b = parse(b)
    except InvalidVersion:
        v_b = None
    if v_a is None:
        return -1 if v_b is not None else (a > b) - (a < b)
    if v_b is None:
        return 1
    return (v_a > v_b) - (v_a < v_b)
