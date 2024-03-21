# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import re
import shutil
from typing import Optional

import packit.upstream
from packit.actions import ActionName
from packit.config.common_package_config import MultiplePackages
from packit.distgit import DistGit

logger = logging.getLogger(__name__)


class ChangelogHelper:
    def __init__(
        self,
        upstream: "packit.upstream.Upstream",
        downstream: Optional[DistGit] = None,
        package_config: Optional[MultiplePackages] = None,
    ) -> None:
        self.up = upstream
        self.dg = downstream
        self.package_config = package_config

    @staticmethod
    def resolve_release_suffix(
        package_config: MultiplePackages,
        release_suffix: Optional[str] = None,
        default_release_suffix: bool = False,
    ) -> Optional[str]:
        """
        Resolves the release suffix value, since it can be set from multiple places
        and also overriden to the default one that is generated by packit.

        Args:
            package_config: Package config that is used as fallback.
            release_suffix: Release suffix that was passed from CLI.
            default_release_suffix: Override for using the default one that ensures
                correct NVR ordering.

        Returns:
            `None` if packit is to use the default method of generating release
            suffix, otherwise string containing the release suffix.
        """
        if default_release_suffix:
            # we want to use the default packit-generated release suffix
            release_suffix = None
        elif release_suffix is None:
            # we want to get release suffix from the configuration
            release_suffix = package_config.release_suffix
        return release_suffix

    def get_entry_from_action(
        self,
        version: Optional[str] = None,
        resolved_bugs: Optional[list[str]] = None,
    ) -> Optional[str]:
        """
        Runs changelog-entry action if present and returns string that can be
        used as a changelog entry.

        Args:
            version: version to be set in specfile
            resolved_bugs: List of bugs that are resolved by the update (e.g. [rhbz#123]).

        Returns:
            Changelog entry or `None` if action is not present.
        """
        resolved_bugs_str = " ".join(resolved_bugs) if resolved_bugs else ""
        env = self.package_config.get_package_names_as_env() | {
            "PACKIT_PROJECT_VERSION": version,
            "PACKIT_RESOLVED_BUGS": resolved_bugs_str,
        }
        messages = self.up.get_output_from_action(ActionName.changelog_entry, env=env)
        if not messages:
            return None

        return "\n".join(line.rstrip() for line in messages)

    @staticmethod
    def sanitize_entry(entry: str) -> str:
        # escape macro references and macro/shell/expression expansions
        # that could break spec file parsing
        entry = re.sub(r"(?<!%)%(?=(\w+|[{[(]))", "%%", entry)
        # prepend asterisk at the start of a line with a space in order
        # not to break identification of entry boundaries
        return re.sub(r"^[*]", " *", entry, flags=re.MULTILINE)

    def update_dist_git(
        self,
        full_version: str,
        upstream_tag: str,
        resolved_bugs: Optional[list[str]] = None,
    ) -> None:
        """
        Update the spec-file in dist-git:
        * Sync content from upstream spec-file.
        * Set 'Version'.
        * Add new entry in the %changelog section
          (if %autochangelog macro is not used).

        Copy the upstream spec-file as is if no spec-file is present in downstream.
        (E.g. for new packages)

        Args:
            full_version: Version to be set in the spec-file.
            upstream_tag: The commit messages after last tag and before this tag are used
                to update the changelog in the spec-file.
            resolved_bugs: List of bugs that are resolved by the update (e.g. [rhbz#123]).
        """
        action_output = self.get_entry_from_action(
            version=full_version,
            resolved_bugs=resolved_bugs,
        )
        comment = (
            action_output
            or (
                self.up.local_project.git_project.get_release(
                    tag_name=upstream_tag,
                    name=full_version,
                ).body
                if self.package_config.copy_upstream_release_description
                # in pull_from_upstream workflow, upstream git_project can be None
                and self.up.local_project.git_project
                else self.up.get_commit_messages(
                    after=self.up.get_last_tag(before=upstream_tag),
                    before=upstream_tag,
                )
            )
            or f"- Update to upstream release {full_version}"
        )
        if not action_output and resolved_bugs:
            comment += "\n"
            for bug in resolved_bugs:
                comment += f"- Resolves: {bug}\n"

        comment = self.sanitize_entry(comment)
        try:
            self.dg.set_specfile_content(
                self.up.specfile,
                full_version,
                comment=None if self.dg.specfile.has_autochangelog else comment,
            )
        except FileNotFoundError as ex:
            # no downstream spec file: this is either a mistake or
            # there is no spec file in dist-git yet, hence warning
            logger.warning(
                f"Unable to find a spec file in downstream: {ex}, copying the one from upstream.",
            )
            shutil.copy2(
                self.up.absolute_specfile_path,
                self.dg.get_absolute_specfile_path(),
            )
            # set the specfile content now that the downstream spec file is present
            self.dg.set_specfile_content(
                self.up.specfile,
                full_version,
                comment=None if self.dg.specfile.has_autochangelog else comment,
            )

    def _get_release_for_source_git(
        self,
        current_commit: str,
        update_release: bool,
        release_suffix: Optional[str],
    ) -> Optional[str]:
        old_release = self.up.specfile.expanded_release
        if release_suffix:
            return f"{old_release}.{release_suffix}"

        if not update_release:
            return None

        try:
            old_release_int = int(old_release)
            new_release = str(old_release_int + 1)
        except ValueError:
            new_release = str(old_release)

        return f"{new_release}.g{current_commit}"

    def prepare_upstream_using_source_git(
        self,
        update_release: bool,
        release_suffix: Optional[str],
    ) -> None:
        """
        Updates changelog when creating SRPM within source-git repository.
        """
        current_commit = self.up.local_project.commit_hexsha
        release_to_update = self._get_release_for_source_git(
            current_commit,
            update_release,
            release_suffix,
        )

        msg = self.get_entry_from_action()
        if not msg and update_release:
            msg = f"- Downstream changes ({current_commit})"
        self.up.specfile.release = release_to_update
        if msg is not None:
            self.up.specfile.add_changelog_entry(msg)

    def prepare_upstream_locally(
        self,
        version: str,
        commit: str,
        update_release: bool,
        release: str,
    ) -> None:
        """
        Updates changelog when creating SRPM within upstream repository.

        Args:
            version: Version to be set in the spec-file.
            commit: Commit to be set in the changelog.
            update_release: Whether to change Release in the spec-file.
            release: Release to be set in the spec-file.
        """
        self.up.specfile.version = version
        last_tag = self.up.get_last_tag()
        msg = self.get_entry_from_action(version=version)
        if not msg and last_tag and update_release:
            msg = self.up.get_commit_messages(after=last_tag)
        if not msg and update_release:
            # no describe, no tag - just a boilerplate message w/ commit hash
            # or, there were no changes b/w HEAD and last_tag, which implies last_tag == HEAD
            msg = f"- Development snapshot ({commit})"
        # instead of changing version, we change Release field
        # upstream projects should take care of versions
        if update_release:
            # Make sure the new release has a dist tag if it is not already included explicitly
            # (in release) or implicitly (in up.specfile.raw_release)
            if (
                release
                and not release.endswith("%{?dist}")
                and not self.up.specfile.raw_release.endswith("%{?dist}")
            ):
                release = f"{release}%{{?dist}}"
            logger.debug(f"Setting Release in spec to {release!r}.")
            self.up.specfile.release = release
        if msg is not None:
            self.up.specfile.add_changelog_entry(msg)
