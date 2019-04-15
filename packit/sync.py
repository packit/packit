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

import glob
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


class RawSyncFilesItem(SyncFilesItem):
    src: str
    dest: str


def get_files_from_wildcard(
    file_wildcard: str, destination: str
) -> List[RawSyncFilesItem]:
    """
    Evaluate globs in file_wildcard
    """
    globed_files = glob.glob(file_wildcard)
    return [RawSyncFilesItem(src=file, dest=destination) for file in globed_files]


def get_raw_files(file_to_sync: SyncFilesItem) -> List[RawSyncFilesItem]:
    """
    Split the  SyncFilesItem with src as a list or wildcard to multiple instances.

    Destination is used from the original SyncFilesItem.
    """
    source = file_to_sync.src
    if not isinstance(source, list):
        source = [source]

    files_to_sync: List[RawSyncFilesItem] = []
    for file in source:
        files_to_sync += get_files_from_wildcard(
            file_wildcard=file, destination=file_to_sync.dest
        )
    return files_to_sync


def sync_files(
    files_to_sync: List[RawSyncFilesItem],
    src_working_dir: str,
    dest_working_dir: str,
    down_to_up: bool = False,
) -> None:
    """
    Copy files b/w upstream and downstream repo.

    When down_to_up is True, we copy from downstream to upstream.
    This implies that src and dest are swapped.
    """
    logger.debug(f"Copy synced files {files_to_sync}")

    for fi in files_to_sync:
        if down_to_up:
            dest = Path(src_working_dir).joinpath(fi.src)
            src = Path(dest_working_dir).joinpath(fi.dest)
        else:
            src = Path(src_working_dir).joinpath(fi.src)
            dest = Path(dest_working_dir).joinpath(fi.dest)
        logger.debug(f"src = {src}, dest = {dest}")
        if src.exists():
            if src.is_dir():
                logger.debug("src is a dir, using copytree")
                shutil.copytree(src, dest)
            else:
                if fi.dest.endswith("/"):
                    logger.info(f"Creating target directory: {dest}")
                    dest.mkdir(parents=True, exist_ok=True)
                logger.info(f"Copying {src} to {dest}.")
                shutil.copy2(src, dest)
        else:
            raise PackitException(f"Path {src} does not exist.")
