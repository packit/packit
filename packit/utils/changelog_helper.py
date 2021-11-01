# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import shutil
import logging
from typing import Optional

from packit.actions import ActionName
from packit.config.common_package_config import CommonPackageConfig
from packit.distgit import DistGit
import packit.upstream

logger = logging.getLogger(__name__)


class ChangelogHelper:
    def __init__(
        self,
        upstream: "packit.upstream.Upstream",
        downstream: Optional[DistGit] = None,
        package_config: Optional[CommonPackageConfig] = None,
    ) -> None:
        self.up = upstream
        self.dg = downstream
        self.package_config = package_config

    @property
    def entry_from_action(self) -> Optional[str]:
        """
        Runs changelog-entry action if present and returns string that can be
        used as a changelog entry.

        Returns:
            Changelog entry or `None` if action is not present.
        """
        messages = self.up.get_output_from_action(ActionName.changelog_entry)
        if not messages:
            return None

        return "\n".join(map(lambda line: line.rstrip(), messages))

    def update_dist_git(self, full_version: str, upstream_tag: str) -> None:
        """
        Updates changelog when running `update-dist-git`.

        Args:
            full_version: Version to be set in the spec-file.
            upstream_tag: The commit message of this commit is going to be used
                to update the changelog in the spec-file.
        """
        comment = self.entry_from_action or (
            self.up.local_project.git_project.get_release(name=full_version).body
            if self.package_config.copy_upstream_release_description
            else self.up.get_commit_messages(
                after=self.up.get_last_tag(upstream_tag), before=upstream_tag
            )
        )
        try:
            self.dg.set_specfile_content(self.up.specfile, full_version, comment)
        except FileNotFoundError as ex:
            # no downstream spec file: this is either a mistake or
            # there is no spec file in dist-git yet, hence warning
            logger.warning(
                f"Unable to find a spec file in downstream: {ex}, copying the one from upstream."
            )
            shutil.copy2(
                self.up.absolute_specfile_path,
                self.dg.get_absolute_specfile_path(),
            )

    def prepare_upstream_using_source_git(self) -> None:
        """
        Updates changelog when creating SRPM within source-git repository.
        """
        old_release = self.up.specfile.get_release_number()
        try:
            old_release_int = int(old_release)
            new_release = str(old_release_int + 1)
        except ValueError:
            new_release = str(old_release)

        current_commit = self.up.local_project.commit_hexsha
        release_to_update = f"{new_release}.g{current_commit}"
        msg = self.entry_from_action or f"- Downstream changes ({current_commit})"
        self.up.specfile.set_spec_version(
            release=release_to_update, changelog_entry=msg
        )

    def prepare_upstream_locally(
        self,
        version: str,
        commit: str,
        bump_version: bool,
        release_suffix: Optional[str],
    ) -> None:
        """
        Updates changelog when creating SRPM within upstream repository.

        Args:
            version: Version to be set in the spec-file.
            commit: Commit to be set in the changelog.
            bump_version: Specifies whether version should be changed in the spec-file.
            release_suffix: Specifies local release suffix. `None` represents default suffix.
        """
        last_tag = self.up.get_last_tag()
        msg = self.entry_from_action
        if not msg and last_tag and bump_version:
            msg = self.up.get_commit_messages(after=last_tag)
        if not msg and bump_version:
            # no describe, no tag - just a boilerplate message w/ commit hash
            # or, there were no changes b/w HEAD and last_tag, which implies last_tag == HEAD
            msg = f"- Development snapshot ({commit})"
        release = self.up.get_spec_release(
            bump_version=bump_version,
            release_suffix=release_suffix,
        )
        logger.debug(f"Setting Release in spec to {release!r}.")
        # instead of changing version, we change Release field
        # upstream projects should take care of versions
        self.up.specfile.set_spec_version(
            version=version,
            release=release,
            changelog_entry=msg,
        )
