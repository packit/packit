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

import logging
import shutil
from pathlib import Path
from typing import List
from typing import NamedTuple, Union

from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


class SyncFilesItem(NamedTuple):
    src: Union[str, List[str]]
    dest: str

    def __repr__(self):
        return f"SyncFilesItem(src={self.src}, dest={self.dest})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SyncFilesItem):
            raise NotImplementedError()

        return self.src == other.src and self.dest == other.dest


class RawSyncFilesItem(NamedTuple):
    src: Path
    dest: Path
    # when dest is specified with trailing slash, it is meant to be a dir
    dest_is_dir: bool

    def __repr__(self):
        return f"RawSyncFilesItem(src={self.src}, dest={self.dest}, dist_is_dir={self.dest_is_dir})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RawSyncFilesItem):
            raise NotImplementedError()

        return (
            self.src == other.src
            and self.dest == other.dest
            and self.dest_is_dir == other.dest_is_dir
        )

    def reversed(self) -> "RawSyncFilesItem":
        return RawSyncFilesItem(
            src=self.dest, dest=self.src, dest_is_dir=self.dest_is_dir
        )


def get_raw_files(
    src_dir: Path, dest_dir: Path, file_to_sync: SyncFilesItem
) -> List[RawSyncFilesItem]:
    """
    Split SyncFilesItem into multiple RawSyncFilesItem instances (src can be a list)

    Destination is used from the original SyncFilesItem.
    """
    source = file_to_sync.src
    if not isinstance(source, list):
        source = [source]
    files_to_sync: List[RawSyncFilesItem] = []
    for file in source:
        globs = src_dir.glob(file)
        target = dest_dir.joinpath(file_to_sync.dest)
        for g in globs:
            files_to_sync.append(
                RawSyncFilesItem(
                    src=g,
                    dest=target,
                    dest_is_dir=True if file_to_sync.dest.endswith("/") else False,
                )
            )
    return files_to_sync


def sync_files(files_to_sync: List[RawSyncFilesItem], fail_on_missing=False) -> None:
    """
    Copy files b/w upstream and downstream repo.
    """
    logger.debug(f"Copy synced files {files_to_sync}")

    for fi in files_to_sync:
        src = Path(fi.src)
        dest = Path(fi.dest)
        logger.debug(f"src = {src}, dest = {dest}")
        if src.exists():
            if src.is_dir():
                logger.debug("`src` is a dir, will use copytree")
                if dest.is_dir():
                    logger.debug(f"Dest dir {dest} exists, rmtree it first")
                    shutil.rmtree(dest, ignore_errors=True)
                logger.info(f"Copying tree {src} to {dest}.")
                shutil.copytree(src, dest)
            else:
                if fi.dest_is_dir:
                    logger.info(f"Creating target directory: {dest}")
                    dest.mkdir(parents=True, exist_ok=True)
                logger.info(f"Copying {src} to {dest}.")
                shutil.copy2(src, dest)
        else:
            if fail_on_missing:
                raise PackitException(f"Path {src} does not exist.")
            else:
                logger.info(f"Path {src} does not exist. Not syncing.")
