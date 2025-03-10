# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
from collections import namedtuple
from datetime import timedelta
from itertools import chain
from typing import Optional, Union

import opensuse_distro_aliases
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

Distro = namedtuple("Distro", ["namever", "branch"])

logger = logging.getLogger(__name__)


@ttl_cache(maxsize=1, ttl=timedelta(hours=12).seconds)
def get_aliases() -> dict[str, list[Distro]]:
    """
    A wrapper around `fedora_distro_aliases.get_distro_aliases()`
    and `opensuse_distro_aliases.get_distro_aliases()`.

    Returns:
        Dict where the key is the alias and the value is a set of `Distro` tuples.

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
    except Exception as e:
        logger.error(
            "Using cached openSUSE distro aliases, "
            f"`opensuse_distro_aliases.get_distro_aliases()` failed: {e}",
        )
        opensuse_aliases = opensuse_distro_aliases.CACHED_ACTIVE_DISTRIBUTION_ALIASES

    return {
        alias: [
            Distro(d.namever, d.branch if hasattr(d, "branch") else d.namever)
            for d in distros
        ]
        for alias, distros in chain(distro_aliases.items(), opensuse_aliases.items())
    }


def expand_aliases(
    *targets: str,
    default: Optional[str] = DEFAULT_VERSION,
) -> set[Union[Distro, str]]:
    """
    Expands aliases in the given list of targets. Also converts
    known distro names and dist-git branch names to `Distro` tuples.

    Args:
        targets: List of targets, e.g. fedora-stable or epel-9.
        default: Default to use if no target was specified.

    Returns:
        Set of `Distro` objects or `$name-$version` strings.
    """
    aliases = get_aliases()
    result: set[Union[Distro, str]] = set()
    for target in list(targets) or ([default] if default else []):
        if target in aliases:
            # expand alias
            result.update(aliases[target])
        else:
            result.update(
                # try to convert target to Distro
                [
                    distro
                    for distro in chain(aliases["fedora-all"], aliases["epel-all"])
                    if target in distro
                ]
                # use the original string
                or [target],
            )
    return result


def get_branches(
    *targets: str,
    default: Optional[str] = DEFAULT_VERSION,
    default_dg_branch: str = "main",
    with_aliases: bool = False,
) -> set[str]:
    """
    Transforms targets into dist-git branch names.

    Args:
        targets: List of targets, e.g. fedora-stable or epel-9.
        default: Default to use if no target was specified.
        default_dg_branch: Default branch of the dist-git repo.
        with_aliases: Whether to include branch aliases, e.g. rawhide for main.
            Defaults to `False`.

    Returns:
        Set of dist-git branch names.
    """

    def branch_name(x):
        if isinstance(x, Distro):
            if x.branch == "rawhide":
                # use default branch instead of rawhide
                return default_dg_branch
            return x.branch
        return x

    branches = {branch_name(x) for x in expand_aliases(*targets, default=default)}
    if with_aliases and default_dg_branch in branches:
        branches.add("rawhide")
    return branches


def get_koji_targets(
    *targets: str,
    default: Optional[str] = DEFAULT_VERSION,
) -> set[str]:
    """
    Transforms targets into Koji target names.

    Args:
        targets: List of targets, e.g. fedora-stable or epel-9.
        default: Default to use if no target was specified.

    Returns:
        Set of Koji target names.
    """

    def koji_target_name(x):
        if isinstance(x, Distro):
            # Koji targets are equal to branch names except for EPEL <= 6
            if x.branch.startswith("el"):
                return x.namever.replace("-", "")
            return x.branch
        return x

    return {koji_target_name(x) for x in expand_aliases(*targets, default=default)}


def get_build_targets(
    *targets: str,
    default: Optional[str] = DEFAULT_VERSION,
) -> set[str]:
    """
    Transforms targets into mock/Copr chroot names.

    Args:
        targets: List of targets, e.g. fedora-stable or epel-9.
        default: Default to use if no target was specified.

    Returns:
        Set of mock/Copr chroot names.
    """

    def chroot_name(x):
        if isinstance(x, Distro):
            if x.namever.startswith("epel-10."):
                # TODO: change this accordingly once mock/Copr chroot names
                #       for minor EPEL versions are known
                return "epel-10"
            return x.namever
        return x

    chroots: set[str] = set()
    for target in list(targets) or ([default] if default else []):
        if target.endswith(tuple(f"-{arch}" for arch in ARCHITECTURE_LIST)):
            namever, arch = target.rsplit("-", maxsplit=1)
        else:
            namever, arch = target, "x86_64"
        chroots.update(
            chroot_name(x) + f"-{arch}"
            for x in expand_aliases(namever, default=default)
        )
    return {DEPRECATED_TARGET_MAP.get(t, t) for t in chroots}


def get_fast_forward_merge_branches_for(
    dist_git_branches: Union[list, dict, set, None],
    source_branch: str,
    default: Optional[str] = DEFAULT_VERSION,
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


def get_all_koji_targets() -> list[str]:
    return run_command(["koji", "list-targets", "--quiet"], output=True).stdout.split()
