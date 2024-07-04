# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import dataclasses
from dataclasses import dataclass
from typing import Optional

from ogr.parsing import RepoUrl, parse_git_repo


@dataclass(frozen=True)
class DistGitInstance:
    hostname: str
    alternative_hostname: Optional[str]
    namespace: str

    def for_sig(self, sig: Optional[str]) -> "DistGitInstance":
        if sig is None:
            return self

        return dataclasses.replace(self, namespace=self.namespace.format(sig=sig))

    @property
    def url(self) -> str:
        return f"https://{self.hostname}/"

    def distgit_project_url(self, package: str) -> str:
        return f"{self.url}{self.namespace}/{package}"

    @staticmethod
    def from_url_and_namespace(url: str, namespace: str) -> "DistGitInstance":
        """Create an instance from the url and namespace.

        Args:
            url: Base URL of the dist-git.
            namespace: Namespace in the dist-git.

        Returns:
            DistGitInstance object.
        """
        parsed_url = RepoUrl._prepare_url(url)
        if parsed_url is None:
            # parsing has failed
            raise ValueError("Parsing of the dist-git URL has failed")

        return DistGitInstance(
            hostname=parsed_url.hostname,
            alternative_hostname=None,
            namespace=namespace,
        )

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
