# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
from datetime import timedelta
from typing import Dict, List, Set

from cachetools.func import ttl_cache

from packit.copr_helper import CoprHelper
from packit.exceptions import PackitException
from packit.utils.bodhi import get_bodhi_client
from packit.utils.commands import run_command
from packit.utils.decorators import fallback_return_value

ALIASES: Dict[str, List[str]] = {
    "fedora-all": ["fedora-35", "fedora-36", "fedora-37", "fedora-rawhide"],
    "fedora-stable": ["fedora-35", "fedora-36"],
    "fedora-development": ["fedora-rawhide", "fedora-37"],
    "fedora-latest": ["fedora-37"],
    "fedora-latest-stable": ["fedora-36"],
    "fedora-branched": ["fedora-35", "fedora-36", "fedora-37"],
    "epel-all": ["epel-7", "epel-8", "epel-9"],
}

ARCHITECTURE_LIST: List[str] = [
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


def get_versions(*name: str, default=DEFAULT_VERSION) -> Set[str]:
    """
    Expand the aliases to the name(s).

    :param name: name(s) of the system and version (e.g. "fedora-30" or "fedora-stable")
    :param default: used if no positional argument was given
    :return: set of string containing system name and version
    """
    if not (default or name):
        return set()

    names = list(name) or [default]
    versions: Set[str] = set()
    for one_name in names:
        versions.update(get_aliases().get(one_name, [one_name]))
    return versions


def get_build_targets(*name: str, default: str = DEFAULT_VERSION) -> Set[str]:
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
    possible_sys_and_versions: Set[str] = set()
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
            }
        )
    possible_sys_and_versions = {
        DEPRECATED_TARGET_MAP.get(target, target)
        for target in possible_sys_and_versions
    }

    return possible_sys_and_versions


def get_valid_build_targets(*name: str, default: str = DEFAULT_VERSION) -> set:
    """
    Function generates set which contains build targets available also in copr chroots.

    :param name: name(s) of the system and version or target name. (passed to
                packit.config.aliases.get_build_targets() function)
            or target name (e.g. "fedora-30-x86_64" or "fedora-stable-x86_64")
    :param default: used if no positional argument was given
    :return: set of build targets available also in copr chroots
    """
    build_targets = get_build_targets(*name, default=default)
    logger.info(f"Build targets: {build_targets} ")
    copr_chroots = CoprHelper.get_available_chroots()
    logger.info(f"Copr chroots: {copr_chroots} ")
    logger.info(f"Result set: {set(build_targets) & set(copr_chroots)}")
    return set(build_targets) & set(copr_chroots)


def get_branches(
    *name: str,
    default: str = DEFAULT_VERSION,
    default_dg_branch: str = "main",
    with_aliases: bool = False,
) -> Set[str]:
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


def get_koji_targets(*name: str, default=DEFAULT_VERSION) -> Set[str]:
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


def get_all_koji_targets() -> List[str]:
    return run_command(["koji", "list-targets", "--quiet"], output=True).stdout.split()


@ttl_cache(maxsize=1, ttl=timedelta(hours=12).seconds)
@fallback_return_value(ALIASES)
def get_aliases() -> Dict[str, List[str]]:
    """
    Function to automatically determine fedora-* and epel-* aliases.
    Current data are fetched via bodhi client, with default base url
    `https://bodhi.fedoraproject.org/'.

    Returns:
        Dictionary containing aliases.
    """
    bodhi_client = get_bodhi_client()
    releases = []
    page = pages = 1
    while page <= pages:
        results = bodhi_client.get_releases(exclude_archived=True, page=page)
        releases.extend(results.releases)
        page += 1
        pages = results.pages
    current_fedora_releases, pending_fedora_releases, epel_releases = [], [], []

    for release in filter(lambda r: r.state in ["current", "pending"], releases):
        if release.id_prefix == "FEDORA" and release.name != "ELN":
            name = release.long_name.lower().replace(" ", "-")
            if release.state == "current":
                current_fedora_releases.append(name)
            else:
                pending_fedora_releases.append(name)
        elif release.id_prefix == "FEDORA-EPEL":
            name = release.name.lower()
            epel_releases.append(name)

    current_fedora_releases.sort(key=lambda x: int(x.rsplit("-")[-1]))
    pending_fedora_releases.sort(key=lambda x: int(x.rsplit("-")[-1]))
    # The Fedora with the highest version is "rawhide", but
    # Bodhi always uses release names, and has no concept of "rawhide".
    pending_fedora_releases[-1] = "fedora-rawhide"

    #  fedora-34   fedora-35   [ fedora-36 ]   fedora-rawhide
    #  current     current  [ current/pending ]  pending
    #
    # all: everything
    # stable: everything marked as "current"
    # development: everything marked as "pending"
    # latest: the latest with a version number
    # latest-stable: the last "current"
    # branched: all with a version number
    return {
        "fedora-all": current_fedora_releases + pending_fedora_releases,
        "fedora-stable": current_fedora_releases,
        "fedora-development": pending_fedora_releases,
        "fedora-latest": pending_fedora_releases[-2:-1] or current_fedora_releases[-1:],
        "fedora-latest-stable": current_fedora_releases[-1:],
        "fedora-branched": current_fedora_releases + pending_fedora_releases[:-1],
        "epel-all": epel_releases,
    }
