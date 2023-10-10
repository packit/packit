# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from typing import Optional

from ogr.parsing import parse_git_repo


@dataclass
class DistGitInstance:
    hostname: str
    alternative_hostname: Optional[str]
    namespace: str

    @property
    def url(self) -> str:
        return f"https://{self.hostname}/"

    def has_repository(self, remote_url: str) -> bool:
        """
        Args:
            remote_url: Remote URL to be decided.

        Returns:
            `True`, if the remote corresponds to dist-git, `False` otherwise.
        """
        parsed_remote = parse_git_repo(remote_url)
        hostname, namespace = parsed_remote.hostname, parsed_remote.namespace

        if hostname is None or namespace is None:
            return False

        return (
            hostname == self.hostname or hostname == self.alternative_hostname
        ) and namespace == self.namespace
