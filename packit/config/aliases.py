# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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

from typing import Dict, List, Set

from packit.exceptions import PackitException
from packit.utils.commands import run_command

ALIASES: Dict[str, List[str]] = {
    "fedora-development": ["fedora-33", "fedora-rawhide"],
    "fedora-stable": ["fedora-31", "fedora-32"],
    "fedora-all": ["fedora-31", "fedora-32", "fedora-33", "fedora-rawhide"],
    "epel-all": ["epel-6", "epel-7", "epel-8"],
}
ARCHITECTURE_LIST: List[str] = [
    "aarch64",
    "armhfp",
    "i386",
    "ppc64le",
    "s390x",
    "x86_64",
]
DEFAULT_VERSION = "fedora-stable"


def get_versions(*name: str, default=DEFAULT_VERSION) -> Set[str]:
    """
    Expand the aliases to the name(s).

    :param name: name(s) of the system and version (e.g. "fedora-30"/"fedora-stable")
    :param default: used if no positional argument was given
    :return: set of string containing system name and version
    """
    if not (default or name):
        return set()

    names = list(name) or [default]
    versions: Set[str] = set()
    for one_name in names:
        versions.update(ALIASES.get(one_name, [one_name]))
    return versions


def get_build_targets(*name: str, default=DEFAULT_VERSION) -> Set[str]:
    """
    Expand the aliases to the name(s) and transfer to the build targets.

    :param name: name(s) of the system and version (e.g. "fedora-30"/"fedora-stable")
            or target name (e.g. "fedora-30-x86_64"/"fedora-stable-x86_64")
    :param default: used if no positional argument was given
    :return: set of build targets
    """
    if not (default or name):
        return set()

    names = list(name) or [default]
    possible_sys_and_versions: Set[str] = set([])
    for one_name in names:
        name_split = one_name.rsplit("-", maxsplit=2)
        l_name_split = len(name_split)

        if l_name_split < 2:  # only one part
            # => cannot guess anything other than rawhide
            if "rawhide" in one_name:
                sys_name, version, architecture = "fedora", "rawhide", "x86_64"
            else:
                err_msg = (
                    "Cannot get build target from '{one_name}'"
                    f", packit understands values like these: '{list(ALIASES.keys())}'."
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
    return possible_sys_and_versions


def get_branches(*name: str, default=DEFAULT_VERSION) -> Set[str]:
    """
    Expand the aliases to the name(s) and transfer to the dist-git branch name.

    :param name: name(s) of the system and version (e.g. "fedora-stable"/"fedora-30")
            or branch name (e.g. "f30"/"epel8")
    :param default: used if no positional argument was given
    :return: set of dist-git branch names
    """
    if not (default or name):
        return set()

    names = list(name) or [default]
    branches = set()

    for sys_and_version in get_versions(*names):
        if "rawhide" in sys_and_version:
            branches.add("master")
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
    return run_command(["koji", "list-targets", "--quiet"], output=True).split()
