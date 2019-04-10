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
from typing import List

from packit.config import PackageConfig, SyncFilesItem, SyncFilesConfig
from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


def get_files_from_wildcard(
    file_wildcard: str, destination: str
) -> List[SyncFilesItem]:
    if "*" not in file_wildcard:
        if file_wildcard.endswith("/"):
            file_wildcard = f"{file_wildcard}*"
        else:
            return [SyncFilesItem(src=file_wildcard, dest=destination)]

    globed_files = glob.glob(file_wildcard)
    return [SyncFilesItem(src=file, dest=destination) for file in globed_files]


def get_raw_files(file_to_sync: SyncFilesItem) -> List[SyncFilesItem]:
    source = file_to_sync.src
    if not isinstance(source, list):
        source = [source]

    files_to_sync: List[SyncFilesItem] = []
    for file in source:
        files_to_sync += get_files_from_wildcard(
            file_wildcard=file, destination=file_to_sync.dest
        )
    return files_to_sync


def get_wildcard_resolved_sync_files(package_config: PackageConfig) -> SyncFilesConfig:
    logger.debug("Packit synced files %s", package_config.synced_files.files_to_sync)
    files_to_sync: List[SyncFilesItem] = []
    for sync in package_config.synced_files.files_to_sync:
        files_to_sync += get_raw_files(file_to_sync=sync)

    logger.debug(f"Resolved synced file {files_to_sync}")
    return SyncFilesConfig(files_to_sync=files_to_sync)


def sync_files(pc: PackageConfig, src_working_dir: str, dest_working_dir: str) -> None:
    """
    Sync required files from upstream to downstream.
    """
    files_config = get_wildcard_resolved_sync_files(pc)
    logger.debug(f"Copy synced files {files_config.files_to_sync}")

    for fi in files_config.files_to_sync:
        # Check if destination dir exists
        # If not create the destination dir
        dest_dir = os.path.join(dest_working_dir, fi.dest)
        logger.debug(f"Destination {dest_dir}")
        # Sync all source file
        src_file = os.path.join(src_working_dir, fi.src)  # type: ignore
        logger.debug(f"Source file {src_file}")
        if os.path.exists(src_file):
            logger.info(f"Syncing {src_file}")
            shutil.copy2(src_file, dest_dir)
        else:
            raise PackitException(
                f"File {src_file} is not present in the upstream repository. "
            )
