import glob
import os
import shutil
import logging

from packit.exceptions import PackitException
from packit.config import PackageConfig, SyncFilesItem, SyncFilesConfig

logger = logging.getLogger(__name__)


def get_wildcard_resolved_sync_files(pc: PackageConfig) -> None:
    logger.debug("Packit synced files %s", pc.synced_files.files_to_sync)
    files_to_sync = []
    for sync in pc.synced_files.files_to_sync:
        source = sync.src
        if isinstance(source, str):
            if "*" not in source:
                if source.endswith("/"):
                    source = f"{source}*"
                else:
                    files_to_sync.append(SyncFilesItem(src=source, dest=sync.dest))
                    continue
        src = glob.glob(source)
        if src:
            for s in src:
                files_to_sync.append(SyncFilesItem(src=s, dest=sync.dest))
    logger.debug(f"Resolved synced file {files_to_sync}")
    pc.synced_files = SyncFilesConfig(files_to_sync=files_to_sync)


def sync_files(pc: PackageConfig, src_working_dir: str, dest_working_dir: str) -> None:
    """
    Sync required files from upstream to downstream.
    """
    get_wildcard_resolved_sync_files(pc)
    logger.debug(f"Copy synced files {pc.synced_files.files_to_sync}")
    for fi in pc.synced_files.files_to_sync:
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
