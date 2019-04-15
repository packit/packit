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
import os
import shutil
from typing import List, NamedTuple, Union

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
    Get list of SyncFilesItem that match the wildcard.

    :param file_wildcard:   - if ends with '/' we add all files of that directory
                            - if contains '*', we use glob.glob to get matches
    :param destination: used to create RawSyncFilesItem instances
    :return: list of matching RawSyncFilesItem instances
    """
    if "*" not in file_wildcard:
        if file_wildcard.endswith("/"):
            file_wildcard = f"{file_wildcard}*"
        else:
            return [RawSyncFilesItem(src=file_wildcard, dest=destination)]

    globed_files = glob.glob(file_wildcard)
    return [RawSyncFilesItem(src=file, dest=destination) for file in globed_files]


def get_raw_files(file_to_sync: SyncFilesItem) -> List[RawSyncFilesItem]:
    """
    Split the  SyncFilesItem with src as a list or wildcard to multiple instances.

    Destination is used from the original SyncFilesItem.

    :param file_to_sync: SyncFilesItem to split
    :return: [RawSyncFilesItem]
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
    files_to_sync: List[RawSyncFilesItem], src_working_dir: str, dest_working_dir: str
) -> None:
    """
    Sync required files from upstream to downstream.
    """
    logger.debug(f"Copy synced files {files_to_sync}")

    for fi in files_to_sync:
        # Check if destination dir exists
        # If not create the destination dir
        dest_dir = os.path.join(dest_working_dir, fi.dest)
        logger.debug(f"Destination {dest_dir}")
        # Sync all source file
        src_file = os.path.join(src_working_dir, fi.src)
        logger.debug(f"Source file {src_file}")
        if os.path.exists(src_file):
            logger.info(f"Syncing {src_file}")
            shutil.copy2(src_file, dest_dir)
        else:
            raise PackitException(
                f"File {src_file} is not present in the upstream repository. "
            )
