# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import configparser

from pathlib import Path
from typing import Dict, List, Union

import pyrpkg

from packit.exceptions import PackitLookasideCacheException


def get_lookaside_sources(
    pkg_tool: str,
    package: str,
    basepath: Union[Path, str],
) -> List[Dict[str, str]]:
    """
    Gets URLs to sources stored in lookaside cache.

    Args:
        pkg_tool: Packaging tool associated with a lookaside cache instance
          to be used to get the URLs.
        package: Package name.
        basepath: Path to a dist-git repo containing the "sources" file.

    Returns:
        List of dicts with path (filename) and URL.

    Raises:
        PackitLookasideCacheException if reading rpkg configuration or
          parsing the "sources" file fails.
    """
    try:
        parser = configparser.ConfigParser()
        parser.read(f"/etc/rpkg/{pkg_tool}.conf")
        config = dict(parser.items(pkg_tool, raw=True))
        cache = pyrpkg.lookaside.CGILookasideCache(
            config["lookasidehash"], config["lookaside"], config["lookaside_cgi"]
        )
        if config.get("lookaside_namespaced", False):
            package = f"rpms/{package}"
    except (configparser.Error, KeyError) as e:
        raise PackitLookasideCacheException("Failed to read rpkg configuration") from e
    try:
        sources = pyrpkg.sources.SourcesFile(Path(basepath) / "sources", "bsd")
    except (pyrpkg.errors.MalformedLineError, ValueError) as e:
        raise PackitLookasideCacheException("Failed to parse sources") from e
    result = []
    for entry in sources.entries:
        url = cache.get_download_url(package, entry.file, entry.hash, entry.hashtype)
        result.append({"path": entry.file, "url": url})
    return result
