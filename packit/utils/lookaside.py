# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import configparser
import logging
import os
from pathlib import Path
from typing import Union

import pyrpkg

from packit.exceptions import PackitLookasideCacheException

logger = logging.getLogger(__name__)


class LookasideCache:
    def __init__(self, pkg_tool: str) -> None:
        """
        Constructs a wrapper around a lookaside cache.

        Args:
            pkg_tool: Packaging tool associated with a lookaside cache instance
            to be used to get the URLs.

        Raises:
            PackitLookasideCacheException, if construction of the wrapper fails,
            e.g can't read or parse the config, or missing settings are required.
        """
        try:
            parser = configparser.ConfigParser()
            parser.read(f"/etc/rpkg/{pkg_tool}.conf")
            self._config = dict(parser.items(pkg_tool, raw=True))
        except configparser.Error as e:
            raise PackitLookasideCacheException(
                "Failed to parse the rpkg config",
            ) from e

        try:
            self.cache = pyrpkg.lookaside.CGILookasideCache(
                self._config["lookasidehash"],
                self._config["lookaside"],
                self._config["lookaside_cgi"],
            )
        except KeyError as e:
            raise PackitLookasideCacheException(
                "Failed to create a CGI for lookaside cache",
            ) from e

    def _get_package(self, package: str) -> str:
        if self._config.get("lookaside_namespaced", False):
            return f"rpms/{package}"
        return package

    def get_sources(
        self,
        basepath: Union[Path, str],
        package: str,
    ) -> list[dict[str, str]]:
        """
        Gets URLs to sources stored in lookaside cache.

        Args:
            basepath: Path to a dist-git repo containing the "sources" file.
            package: Package name.

        Returns:
            List of dicts with path (filename) and URL.

        Raises:
            PackitLookasideCacheException, if parsing the "sources" file fails.
        """
        try:
            sources = pyrpkg.sources.SourcesFile(Path(basepath) / "sources", "bsd")
        except (pyrpkg.errors.MalformedLineError, ValueError) as e:
            raise PackitLookasideCacheException("Failed to parse sources") from e
        result = []
        for entry in sources.entries:
            url = self.cache.get_download_url(
                self._get_package(package),
                entry.file,
                entry.hash,
                entry.hashtype,
            )
            result.append({"path": entry.file, "url": url})
        return result

    def is_archive_uploaded(self, package: str, archive_path: Union[Path, str]) -> bool:
        """
        We are using a name to check the presence in the lookaside cache.
        (This is the same approach fedpkg itself uses.)
        """
        archive_name = os.path.basename(archive_path)
        archive_hash = self.cache.hash_file(archive_path)

        return self.cache.remote_file_exists_head(
            name=self._get_package(package),
            filename=archive_name,
            hash=archive_hash,
            # `hashtype` is a required argument, yet it doesn't have a default…
            hashtype=None,
        )
