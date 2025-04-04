# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
from datetime import date, datetime
from typing import Callable, Optional, Union

import koji
from specfile.changelog import ChangelogEntry
from specfile.utils import NEVR

from packit.constants import KOJI_BASEURL

logger = logging.getLogger(__name__)


class SessionWrapper:
    def __init__(self) -> None:
        self.session = self._open_session()

    def __getattr__(self, name: str) -> Callable:
        if name in self.__dict__:
            return self.__dict__[name]
        return self._wrap(getattr(self.session, name))

    def _open_session(self) -> koji.ClientSession:
        return koji.ClientSession(baseurl=KOJI_BASEURL)

    def _wrap(self, call: Callable) -> Callable:
        call_name = f"{call._VirtualMethod__name}()"  # type: ignore[attr-defined]

        def wrapper(*args, **kwargs):
            exceptions = []
            while True:
                try:
                    return call(*args, **kwargs)
                except koji.ActionNotAllowed as e:  # noqa: PERF203
                    if (type(e), e.faultCode, e.args) in exceptions:
                        # break the loop if the same exception has already occurred
                        raise
                    exceptions.append((type(e), e.faultCode, e.args))
                    logger.debug(
                        f"{call_name} requires authenticated Koji session, logging in",
                    )
                    self.session.gssapi_login()
                    continue
                except koji.AuthError as e:
                    if (type(e), e.faultCode, e.args) in exceptions:
                        # break the loop if the same exception has already occurred
                        raise
                    exceptions.append((type(e), e.faultCode, e.args))
                    logger.debug(
                        f"Koji session authentication error during {call_name}: {e};"
                        "opening new session",
                    )
                    self.session = self._open_session()
                    continue

        return wrapper


class KojiHelper:
    def __init__(self) -> None:
        self.session = SessionWrapper()

    def get_builds(self, package: str, since: datetime) -> list[dict]:
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

    def get_nvrs(self, package: str, since: datetime) -> list[str]:
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
                package=package,
                tag=tag,
                inherit=True,
                latest=True,
                strict=True,
            )
        except Exception as e:
            logger.debug(
                f"Failed to get latest build of package {package} in tag {tag} from Koji: {e}",
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

    def get_latest_candidate_build(
        self,
        package: str,
        dist_git_branch: str,
    ) -> Optional[dict]:
        """
        Gets the latest build of a package tagged into the candidate tag for the given branch.

        Args:
            package: Package name.
            dist_git_branch: dist-git branch name.

        Returns:
            Latest build or None if there is no such build.
        """
        if not (tag := self.get_candidate_tag(dist_git_branch)):
            return None
        return self.get_latest_build_in_tag(package, tag)

    def get_latest_stable_build(
        self,
        package: str,
        dist_git_branch: str,
        include_candidate: bool = False,
    ) -> Optional[dict]:
        """
        Gets the latest build of a package tagged into any stable or, if requested,
        the candidate tag for the given branch.

        Args:
            package: Package name.
            dist_git_branch: dist-git branch name.
            include_candidate: Whether to consider also builds tagged
              into the corresponding candidate tag.

        Returns:
            Latest build or None if there is no such build.
        """
        if not (candidate_tag := self.get_candidate_tag(dist_git_branch)):
            return None
        tags = self.get_stable_tags(candidate_tag)
        if include_candidate:
            tags.append(candidate_tag)
        return max(
            (self.get_latest_build_in_tag(package, t) for t in tags),
            key=lambda b: NEVR.from_string(b["nvr"]),
        )

    def get_latest_stable_nvr(
        self,
        package: str,
        dist_git_branch: str,
        include_candidate: bool = False,
    ) -> Optional[dict]:
        """
        Gets the NVR of the latest build of a package tagged into any stable or, if requested,
        the candidate tag for the given branch.

        Args:
            package: Package name.
            dist_git_branch: dist-git branch name.
            include_candidate: Whether to consider also builds tagged
              into the corresponding candidate tag.

        Returns:
            NVR of the latest build or None if there is no such build.
        """
        build = self.get_latest_stable_build(
            package,
            dist_git_branch,
            include_candidate,
        )
        if not build:
            return None
        return build["nvr"]

    def get_build_tags(self, nvr: str) -> list[str]:
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

    def get_build_changelog(self, nvr: str) -> list[tuple[int, str, str]]:
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
                rpmID=f"{nvr}.src",
                headers=requested_headers,
                strict=True,
            )
        except Exception as e:
            logger.debug(f"Failed to get changelog of build {nvr} from Koji: {e}")
            return []
        for k, v in headers.items():
            if not isinstance(v, list):
                headers[k] = [v]
        return list(zip(*[headers[h] for h in requested_headers]))

    def get_builds_in_tag(self, tag: str) -> list[dict]:
        """
        Gets list of builds tagged into the specified tag.

        Args:
            tag: Tag name.

        Returns:
            List of builds.
        """
        try:
            builds = self.session.listTagged(
                tag=tag,
                inherit=False,
                latest=False,
                strict=True,
            )
        except Exception as e:
            logger.debug(f"Failed to get builds tagged into {tag} from Koji: {e}")
            return []
        return builds

    def get_build_info(self, build: Union[int, str]) -> Optional[dict]:
        """
        Gets build information.

        Args:
            build: Koji build ID or NVR.

        Returns:
            Build information or None if there is no such build.
        """
        try:
            info = self.session.getBuild(build)
        except Exception as e:
            logger.debug(f"Failed to get build info of {build} from Koji: {e}")
            return None
        return info

    def get_tag_info(self, tag: str) -> Optional[dict]:
        """
        Gets tag information.

        Args:
            tag: Koji tag.

        Returns:
            Tag information or None if there is no such tag.
        """
        try:
            info = self.session.getBuildConfig(tag)
        except Exception as e:
            logger.debug(f"Failed to get tag info of {tag} from Koji: {e}")
            return None
        return info

    def create_sidetag(self, dist_git_branch: str) -> Optional[dict]:
        """
        Creates a new sidetag for the specified dist-git branch.

        Attempts to log in if the underlying session is not authenticated.

        Args:
            dist_git_branch: dist-git branch name.

        Returns:
            New tag information or None if creation failed.
        """
        if not (target := self.get_build_target(dist_git_branch)):
            logger.debug(f"Failed to get build target for {dist_git_branch} from Koji")
            return None
        if not (build_tag := target.get("build_tag_name")):
            logger.debug(f"Failed to get build tag for {dist_git_branch}")
            return None
        try:
            info = self.session.createSideTag(build_tag)
        except Exception as e:
            logger.debug(f"Failed to create sidetag for {build_tag} in Koji: {e}")
            return None
        return info

    def remove_sidetag(self, sidetag: str) -> None:
        """
        Removes the specified sidetag.

        Attempts to log in if the underlying session is not authenticated.

        Args:
            sidetag: Sidetag name.
        """
        try:
            self.session.removeSideTag(sidetag)
        except Exception as e:
            logger.debug(f"Failed to remove sidetag {sidetag} in Koji: {e}")

    def tag_build(self, nvr: str, tag: str) -> Optional[str]:
        """
        Tags a build into the specified tag.

        Attempts to log in if the underlying session is not authenticated.

        Args:
            nvr: NVR of the build.
            tag: Tag name.

        Returns:
            Task ID if tagging was successfully requested else None.
        """
        try:
            task_id = self.session.tagBuild(tag, nvr)
        except Exception as e:
            logger.debug(f"Failed to tag {nvr} into {tag} in Koji: {e}")
            return None
        return str(task_id)

    def untag_build(self, nvr: str, tag: str) -> None:
        """
        Untags a build from the specified tag.

        Attempts to log in if the underlying session is not authenticated.

        Args:
            nvr: NVR of the build.
            tag: Tag name.
        """
        try:
            self.session.untagBuild(tag, nvr, strict=True)
        except Exception as e:
            logger.debug(f"Failed to untag {nvr} from {tag} in Koji: {e}")

    def get_build_target(self, dist_git_branch: str) -> Optional[dict]:
        """
        Gets a build target from a dist-git branch name.

        Args:
            dist_git_branch: dist-git branch name.

        Returns:
            Build target or None if not found.
        """
        target_name = self.get_build_target_name(dist_git_branch)
        try:
            target = self.session.getBuildTarget(target_name, strict=True)
        except Exception as e:
            logger.debug(f"Failed to get build target {target_name} from Koji: {e}")
            return None
        return target

    def get_branch_from_target_name(self, target_name: str) -> Optional[str]:
        """
        Gets a dist-git branch name from a build target name.

        Args:
            target_name: Build target name.

        Returns:
            dist-git branch name or None if not found.
        """
        try:
            target = self.session.getBuildTarget(target_name, strict=True)
        except Exception as e:
            logger.debug(f"Failed to get build target {target_name} from Koji: {e}")
            return None
        if not (dest_tag := target.get("dest_tag_name")):
            logger.debug(f"Failed to get dest tag of {target_name}")
            return None
        # special cases where branch names don't match tag names
        for branch in ["rawhide", "epel10"]:
            if dest_tag == self.get_candidate_tag(branch):
                return branch
        if not (stable_tags := self.get_stable_tags(dest_tag)):
            return None
        # the tag on top of the inheritance chain should match branch name
        return stable_tags[-1]

    # | Overview of tag names
    # |------------------------------|----------------------|-------------------------|
    # |                              | Fedora               | EPEL                    |
    # |------------------------------|----------------------|-------------------------|
    # | fresh build                  | fN-updates-candidate | epelN-testing-candidate |
    # | associated update in testing | fN-updates-testing   | epelN-testing           |
    # | associated update in stable  | fN-updates/fN        | epelN                   |
    # |------------------------------|----------------------|-------------------------|

    def get_candidate_tag(self, dist_git_branch: str) -> Optional[str]:
        """
        Gets a candidate tag from a dist-git branch name.

        Args:
            dist_git_branch: dist-git branch name.

        Returns:
            Name of matching candidate tag or None if not found.
        """
        if not (target := self.get_build_target(dist_git_branch)):
            logger.debug(f"Failed to get build target for {dist_git_branch} from Koji")
            return None
        if not (dest_tag := target.get("dest_tag_name")):
            logger.debug(f"Failed to get dest tag for {dist_git_branch}")
            return None
        return dest_tag

    def get_stable_tags(self, tag: str) -> list[str]:
        """
        Gets a list of stable tags from the specified tag. Only tags without any suffix
        and tags with "-updates" suffix are considered stable.

        Args:
            tag: Tag name.

        Returns:
            List of stable tags. Can be empty.
        """
        try:
            ancestors = self.session.getFullInheritance(tag)
        except Exception as e:
            logger.debug(f"Failed to get inheritance of {tag} from Koji: {e}")
            return []
        tags = [tag] + [a["name"] for a in ancestors]
        return [t for t in tags if "-" not in t or t.endswith("-updates")]

    @staticmethod
    def get_build_target_name(dist_git_branch: str) -> str:
        """
        Gets a build target name from a dist-git branch name.

        Args:
            dist_git_branch: dist-git branch name.

        Returns:
            Name of matching build target.
        """
        if dist_git_branch in ["rawhide", "main"]:
            return "rawhide"
        return f"{dist_git_branch}-candidate"

    @staticmethod
    def format_changelog(changelog: list[tuple[int, str, str]], since: int = 0) -> str:
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
                str(ChangelogEntry.assemble(timestamp, name, text.splitlines())),
            )
        return "\n".join(lines)
