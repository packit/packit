# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
from datetime import date, datetime
from typing import List, Optional, Tuple

import koji

from specfile.changelog import ChangelogEntry
from packit.constants import KOJI_BASEURL

logger = logging.getLogger(__name__)


class KojiHelper:
    """
    Class for querying Koji.

    Attributes:
        session: Koji client session.
    """

    def __init__(self, session: Optional[koji.ClientSession] = None) -> None:
        self.session = (
            session if session is not None else koji.ClientSession(baseurl=KOJI_BASEURL)
        )

    def get_builds(self, package: str, since: datetime) -> List[dict]:
        """
        Gets list of builds of a package since the specified datetime.

        Args:
            package: Package name.
            since: Only builds newer than this datetime will be considered.

        Returns:
            List of builds.
        """
        try:
            package_id = self.session.getPackageID(package, strict=True)
        except Exception as e:
            logger.debug(f"Failed to get ID of package {package} from Koji: {e}")
            return []
        try:
            builds = self.session.listBuilds(
                packageID=package_id,
                state=koji.BUILD_STATES["COMPLETE"],
                completeAfter=since.timestamp(),
            )
        except Exception as e:
            logger.debug(f"Failed to get builds of package {package} from Koji: {e}")
            return []
        if not builds:
            logger.debug(f"No builds found for package {package} since {since}")
            return []
        return builds

    def get_nvrs(self, package: str, since: datetime) -> List[str]:
        """
        Gets list of nvr for builds of a package since the specified datetime.

        Args:
            package: Package name.
            since: Only builds newer than this datetime will be considered.

        Returns:
            List of NVRs.
        """
        return [b["nvr"] for b in self.get_builds(package, since)]

    def get_latest_build_in_tag(self, package: str, tag: str) -> Optional[dict]:
        """
        Gets the latest build of a package tagged into the specified tag.

        Args:
            package: Package name.
            tag: Koji tag.

        Returns:
            Latest build or None if there is no such build.
        """
        try:
            builds = self.session.listTagged(
                package=package, tag=tag, inherit=True, latest=True, strict=True
            )
        except Exception as e:
            logger.debug(
                f"Failed to latest build of package {package} in tag {tag} from Koji: {e}"
            )
            return None
        if not builds:
            return None
        return builds[0]

    def get_latest_nvr_in_tag(self, package: str, tag: str) -> Optional[str]:
        """
        Gets the latest build of a package tagged into the specified tag.

        Args:
            package: Package name.
            tag: Koji tag.

        Returns:
            NVR of the latest build or None if there is no such build.
        """
        build = self.get_latest_build_in_tag(package, tag)
        if not build:
            return None
        return build["nvr"]

    def get_build_tags(self, nvr: str) -> List[str]:
        """
        Gets tags the specified build is tagged into.

        Args:
            nvr: NVR of the build.

        Returns:
            List of tag names.
        """
        try:
            tags = self.session.listTags(build=nvr)
        except Exception as e:
            logger.debug(f"Failed to get tags of build {nvr} from Koji: {e}")
            return []
        return [t["name"] for t in tags]

    def get_build_changelog(self, nvr: str) -> List[Tuple[int, str, str]]:
        """
        Gets changelog associated with SRPM of the specified build.

        Args:
            nvr: NVR of the build.

        Returns:
            List of changelog entries in form of (timestamp, author, content) tuples.
        """
        requested_headers = ["changelogtime", "changelogname", "changelogtext"]
        try:
            headers = self.session.getRPMHeaders(
                rpmID=f"{nvr}.src", headers=requested_headers, strict=True
            )
        except Exception as e:
            logger.debug(f"Failed to get changelog of build {nvr} from Koji: {e}")
            return []
        for k, v in headers.items():
            if not isinstance(v, list):
                headers[k] = [v]
        return list(zip(*[headers[h] for h in requested_headers]))

    @staticmethod
    def format_changelog(changelog: List[Tuple[int, str, str]], since: int = 0) -> str:
        """
        Formats changelog entries since the specified timestamp.

        Args:
            changelog: Changelog as a list of entries in form of
              (timestamp, author, content) tuples.
            since: Only entries newer than this timestamp will be included.

        Returns:
            Formatted changelog as a string.
        """
        lines = []
        for time, name, text in changelog:
            if time <= since:
                break
            timestamp = date.fromtimestamp(time)
            lines.append(
                str(ChangelogEntry.assemble(timestamp, name, text.splitlines()))
            )
        return "\n".join(lines)

    # | Overview of tag names
    # |------------------------------|----------------------|-------------------------|
    # |                              | Fedora               | EPEL                    |
    # |------------------------------|----------------------|-------------------------|
    # | fresh build                  | fN-updates-candidate | epelN-testing-candidate |
    # | associated update in testing | fN-updates-testing   | epelN-testing           |
    # | associated update in stable  | fN-updates/fN        | epelN                   |
    # |------------------------------|----------------------|-------------------------|

    @staticmethod
    def get_candidate_tag(dist_git_branch: str) -> str:
        """
        Gets a candidate tag from a dist-git branch name.

        E.g. for branch f37 the result would be f37-updates-candidate,
        for epel8 branch it would be epel8-testing-candidate.

        Args:
            dist_git_branch: dist-git branch name.

        Returns:
            Name of matching candidate tag.
        """
        if dist_git_branch.startswith("epel"):
            return f"{dist_git_branch}-testing-candidate"
        return f"{dist_git_branch}-updates-candidate"

    @staticmethod
    def get_stable_tags(tag: str) -> List[str]:
        """
        Gets a list of stable tags from the specified tag name.

        E.g. for tag f37-updates-testing the result would be [f37-updates, f37],
        for epel8-testing-candidate it would be [epel8].

        Args:
            tag: Tag name.

        Returns:
            List of stable tags deduced. Can be empty.
        """
        if not tag.endswith("-candidate") and not tag.endswith("-testing"):
            return []
        stable_tag = tag.removesuffix("-candidate").removesuffix("-testing")
        if stable_tag.endswith("-updates"):
            return [stable_tag, stable_tag.removesuffix("-updates")]
        return [stable_tag]
