# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Functions and classes dealing with syncing files between repositories
"""

import glob
import logging
from pathlib import Path
from typing import List, Optional, Union, Sequence

from packit.exceptions import PackitException
from packit.utils import run_command

logger = logging.getLogger(__name__)


def check_subpath(subpath: Path, path: Path) -> Path:
    """Check if 'subpath' is a subpath of 'path'

    Args:
        subpath: Subpath to be checked.
        path: Path agains which subpath is checked.

    Returns:
        'subpath', resolved, in case it is a subpath of 'path'.

    Raises:
        PackitException, if 'subpath' is not a subpath of 'path'.
    """
    if not subpath.resolve().is_relative_to(path.resolve()):
        raise PackitException(
            f"Sync files: Illegal path! {subpath} is not in the subpath of {path}."
        )
    return subpath.resolve()


class SyncFilesItem:
    """Some files to sync to destination

    Think about this as a wrapper around 'rsync'.

    Attributes:
        src: List of paths to sync.
        dest: Destination to sync to.
        mkpath: Create the destination's path component.
    """

    def __init__(
        self,
        src: Sequence[Union[str, Path]],
        dest: Union[str, Path],
        mkpath: bool = False,
    ):
        self.src = [Path(s) for s in src]
        self.dest = Path(dest)
        self.mkpath = mkpath

    def __repr__(self):
        return f"SyncFilesItem(src={self.src}, dest={self.dest}, mkpath={self.mkpath})"

    def __str__(self):
        return " ".join(self.command())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SyncFilesItem):
            raise NotImplementedError()

        return self.src == other.src and self.dest == other.dest

    def command(self, fail_on_missing: bool = False) -> List[str]:
        """Provide to command to do the sync

        Args:
            fail_on_missing: Flag to make the command fail if any of
                the sources are missing.

        Returns:
            The command to do the sync, as a list of strings.
        """
        command = ["rsync", "--archive"]
        if self.mkpath:
            command += ["--mkpath"]
        if not fail_on_missing:
            command += ["--ignore-missing-args"]
        for src in self.src:
            globs = glob.glob(str(src))
            if globs:
                command += globs
            else:
                # 'globs' is an empty list if 'src' is missing, which could
                # render the 'rsync' command meaningless.
                # Make sure 'src' is part of the command in these cases,
                # and let --ignore-missing-args handle the rest.
                command += [str(src)]
        command += [str(self.dest)]
        return command

    def resolve(self, src_base: Path = Path.cwd(), dest_base: Path = Path.cwd()):
        """Resolve all paths and check they are relative to src_base and dest_base

        Args:
            src_base: Base directory for all src items.
            dest_base: Base directory for dest.
        """
        self.src = [check_subpath(src_base / path, src_base) for path in self.src]
        self.dest = check_subpath(dest_base / self.dest, dest_base)

    def drop_src(
        self, src: Union[str, Path], criteria=lambda x, y: x == Path(y)
    ) -> Optional["SyncFilesItem"]:
        """Remove 'src' from the list of src-s

        Args:
            src: A path to be removed.
            criteria: Function to tell if a src should be removed.
                Receives two arguments: the src item inspected and
                'src' received by this method.
        Returns:
            A *new* SyncFilesItem instance if the internal src list
            has still some items left after 'src' is removed.
            Otherwise returns None.
        """
        new_src = [s for s in self.src if not criteria(s, src)]
        if new_src:
            return SyncFilesItem(new_src, self.dest)
        else:
            return None


def iter_srcs(synced_files: Sequence[SyncFilesItem]):
    """Iterate over all the src-s in a list of SyncFilesItem

    Args:
        synced_files: List of SyncFilesItem.

    Yields:
        src-s from every SyncFilesItem, one by one.
    """
    for item in synced_files:
        yield from item.src


def sync_files(synced_files: Sequence[SyncFilesItem]):
    """
    Copy files b/w upstream and downstream repo.
    """
    for item in synced_files:
        run_command(item.command(), print_live=True)
