# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
from datetime import timedelta
from itertools import chain
from typing import Union

import opensuse_distro_aliases
import requests
from cachetools.func import ttl_cache
from fedora_distro_aliases import get_distro_aliases
from fedora_distro_aliases.cache import BadCache

from packit.constants import FAST_FORWARD_MERGE_INTO_KEY
from packit.exceptions import PackitException
from packit.utils.commands import run_command

ARCHITECTURE_LIST: list[str] = [
    "aarch64",
    "armhfp",
    "i386",
    "ppc64le",
    "s390x",
    "x86_64",
]

DEPRECATED_TARGET_MAP = {"centos-stream": "centos-stream-8"}
DEPRECATED_TARGET_MAP = {
    f"{k}-{x}": f"{v}-{x}"
    for k, v in DEPRECATED_TARGET_MAP.items()
    for x in ARCHITECTURE_LIST
}

DEFAULT_VERSION = "fedora-stable"

logger = logging.getLogger(__name__)


def get_versions(*name: str, default=DEFAULT_VERSION) -> set[str]:
    """
    Expand the aliases to the name(s).

    :param name: name(s) of the system and version (e.g. "fedora-30" or "fedora-stable")
    :param default: used if no positional argument was given
    :return: set of string containing system name and version
    """
    if not (default or name):
        return set()

    names = list(name) or [default]
    versions: set[str] = set()
    for one_name in names:
        versions.update(get_aliases().get(one_name, [one_name]))
    return versions


def get_build_targets(*name: str, default: str = DEFAULT_VERSION) -> set[str]:
    """
    Expand the aliases to the name(s) and transfer to the build targets.

    :param name: name(s) of the system and version (e.g. "fedora-30" or "fedora-stable")
            or target name (e.g. "fedora-30-x86_64" or "fedora-stable-x86_64")
    :param default: used if no positional argument was given
    :return: set of build targets
    """
    if not (default or name):
        return set()

    names = list(name) or [default]
    possible_sys_and_versions: set[str] = set()
    for one_name in names:
        name_split = one_name.rsplit("-", maxsplit=2)
        l_name_split = len(name_split)

        if l_name_split < 2:  # only one part
            # => cannot guess anything other than rawhide
            if "rawhide" in one_name:
                sys_name, version, architecture = "fedora", "rawhide", "x86_64"

            else:
                err_msg = (
                    f"Cannot get build target from '{one_name}'"
                    f", packit understands values like these: '{list(get_aliases().keys())}'."
                )
                raise PackitException(err_msg.format(one_name=one_name))

        elif l_name_split == 2:  # "name-version"
            sys_name, version = name_split
            architecture = "x86_64"  # use the x86_64 as a default

        else:  # "name-version-architecture"
            sys_name, version, architecture = name_split
            if architecture not in ARCHITECTURE_LIST:
                # we don't know the architecture => probably wrongly parsed
                # (e.g. "opensuse-leap-15.0")
                sys_name, version, architecture = (
                    f"{sys_name}-{version}",
                    architecture,
                    "x86_64",
                )

        possible_sys_and_versions.update(
            {
                f"{sys_and_version}-{architecture}"
                for sys_and_version in get_versions(f"{sys_name}-{version}")
            },
        )
    return {
        DEPRECATED_TARGET_MAP.get(target, target)
        for target in possible_sys_and_versions
    }


def get_branches(
    *name: str,
    default: str = DEFAULT_VERSION,
    default_dg_branch: str = "main",
    with_aliases: bool = False,
) -> set[str]:
    """
    Expand the aliases to the name(s) and transfer to the dist-git branch name.

    Args:
        name: Name(s) of the system and version (e.g. "fedora-stable"
            or "fedora-30") or branch name (e.g. "f30" or "epel8").
        default: Used if no positional argument was given.
        default_dg_branch: Default branch of dist-git repository.
        with_aliases: If set to `True`, returns branches including aliases.
            Can be used for reacting to webhooks where push can be done against
            either the branch itself or its alias.

            Defaults to `False`.

    Returns:
        Set of dist-git branch names.
    """
    if not (default or name):
        return set()

    names = list(name) or [default]
    branches = set()

    for sys_and_version in get_versions(*names):
        if "rawhide" in sys_and_version:
            branches.add(default_dg_branch)
            if with_aliases:
                branches.add("rawhide")
        elif sys_and_version.startswith("fedora"):
            sys, version = sys_and_version.rsplit("-", maxsplit=1)
            branches.add(f"f{version}")
        elif sys_and_version.startswith("epel"):
            split = sys_and_version.rsplit("-", maxsplit=1)
            if len(split) < 2:
                branches.add(sys_and_version)
                continue
            sys, version = sys_and_version.rsplit("-", maxsplit=1)
            if version.isnumeric() and int(version) <= 6:
                branches.add(f"el{version}")
            else:
                branches.add(f"epel{version}")
        else:
            # We don't know, let's leave the original name.
            branches.add(sys_and_version)

    return branches


def get_fast_forward_merge_branches_for(
    dist_git_branches: Union[list, dict, set, None],
    source_branch: str,
    default: str = DEFAULT_VERSION,
    default_dg_branch: str = "main",
    with_aliases: bool = False,
) -> set[str]:
    """
    Returns a list of target branches that can be fast forwarded merging
    the specified source_branch
    The keys can be aliases, expand them into a temporary structure
    to be sure that source_branch can be found in the first dictionary.
    In the inner loop of the downstream sync the expanded aliases are used.

    The branches should be specified as in the following example
        {"rawhide": {"fast_forward_merge_into": ["f40", "f39"]},
         "epel9": {}
        }

    dist_git_branches: dist_git_branches config key; can be a list or dict
    source_branch: source branch with commits to be merged
    default: the same as get_branches default parameter
    default_dg_branch: the same as get_branches default_dg_branch parameter
    with_aliases: the same as get_branches with_aliases parameter
    """
    if not isinstance(dist_git_branches, dict):
        return set()

    expanded_dist_git_branches = {}
    for key, value in dist_git_branches.items():
        expanded_keys = get_branches(
            *[key],
            default=default,
            default_dg_branch=default_dg_branch,
            with_aliases=True,
        )
        expanded_dist_git_branches.update(
            {expanded_key: value for expanded_key in expanded_keys},
        )

    if source_branch not in expanded_dist_git_branches:
        return set()

    if (source_branch_dict := expanded_dist_git_branches[source_branch]) and isinstance(
        source_branch_dict[FAST_FORWARD_MERGE_INTO_KEY],
        list,
    ):
        return get_branches(
            *source_branch_dict[FAST_FORWARD_MERGE_INTO_KEY],
            default=default,
            default_dg_branch=default_dg_branch,
            with_aliases=with_aliases,
        )

    return set()


def get_koji_targets(*name: str, default=DEFAULT_VERSION) -> set[str]:
    if not (default or name):
        return set()

    names = list(name) or [default]
    targets = set()

    for sys_and_version in get_versions(*names):
        if sys_and_version == "fedora-rawhide":
            targets.add("rawhide")
        elif sys_and_version.startswith("fedora"):
            sys, version = sys_and_version.rsplit("-", maxsplit=1)
            targets.add(f"f{version}")
        elif sys_and_version.startswith("el") and sys_and_version[2:].isnumeric():
            targets.add(f"epel{sys_and_version[2:]}")
        elif sys_and_version.startswith("epel"):
            split = sys_and_version.rsplit("-", maxsplit=1)
            if len(split) == 2:
                sys, version = split
                if version.isnumeric():
                    targets.add(f"epel{version}")
                    continue
            targets.add(sys_and_version)
        else:
            # We don't know, let's leave the original name.
            targets.add(sys_and_version)

    return targets


def get_all_koji_targets() -> list[str]:
    return run_command(["koji", "list-targets", "--quiet"], output=True).stdout.split()


@ttl_cache(maxsize=1, ttl=timedelta(hours=12).seconds)
def get_aliases() -> dict[str, list[str]]:
    """
    A wrapper around `fedora_distro_aliases.get_distro_aliases()` and
    `opensuse_distro_aliases.get_distro_aliases()`.

    Returns:
        Dictionary containing aliases, the key is the distribution group and the
        values is a list of `$name-$version` for the distros belonging to this
        group.

    Raises:
        `PackitException` if aliases cache is not available.
    """
    try:
        # fedora-distro-aliases caches each successful response from Bodhi
        # in ~/.cache/fedora-distro-aliases/cache.json and this cache is used
        # instead of live data in case Bodhi is not accessible
        distro_aliases = get_distro_aliases(cache=True)

    except BadCache as ex:
        raise PackitException(f"Aliases cache unavailable: {ex}") from ex

    try:
        opensuse_aliases = opensuse_distro_aliases.get_distro_aliases()
    except requests.RequestException:
        opensuse_aliases = opensuse_distro_aliases.CACHED_ACTIVE_DISTRIBUTION_ALIASES

    return {
        alias: [d.namever for d in distros]
        for alias, distros in chain(distro_aliases.items(), opensuse_aliases.items())
    }
