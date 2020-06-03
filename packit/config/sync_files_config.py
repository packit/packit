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

import logging
from pathlib import Path
from typing import List

from packit.sync import RawSyncFilesItem, SyncFilesItem, get_raw_files

logger = logging.getLogger(__name__)


class SyncFilesConfig:
    def __init__(self, files_to_sync: List[SyncFilesItem]):
        self.files_to_sync: List[SyncFilesItem] = files_to_sync

    def __repr__(self):
        return f"SyncFilesConfig({self.files_to_sync!r})"

    def get_raw_files_to_sync(
        self, src_dir: Path, dest_dir: Path
    ) -> List[RawSyncFilesItem]:
        """
        Evaluate sync_files: render globs and prepend full paths
        """
        raw_files_to_sync: List[RawSyncFilesItem] = []
        for sync in self.files_to_sync:
            raw_files_to_sync += get_raw_files(src_dir, dest_dir, sync)
        return raw_files_to_sync

    @classmethod
    def get_from_dict(cls, raw_dict: dict) -> "SyncFilesConfig":
        # required to avoid cyclical imports
        from packit.schema import SyncFilesConfigSchema

        config = SyncFilesConfigSchema().load_config(raw_dict)
        logger.debug(f"Loaded config: {config}")

        return config

    def __eq__(self, other: object):
        if not isinstance(other, SyncFilesConfig):
            return NotImplemented

        if not self.files_to_sync and not other.files_to_sync:
            return True

        if len(self.files_to_sync) != len(other.files_to_sync):
            return False

        return self.files_to_sync == other.files_to_sync
