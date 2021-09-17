# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import shutil
import logging
from typing import Optional

from packit.distgit import DistGit
from packit.config.common_package_config import CommonPackageConfig
import packit

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

    def update_dist_git(self, full_version: str, upstream_tag: str) -> None:
        comment = (
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
        old_release = self.up.specfile.get_release_number()
        try:
            old_release_int = int(old_release)
            new_release = str(old_release_int + 1)
        except ValueError:
            new_release = str(old_release)

        current_commit = self.up.local_project.commit_hexsha
        release_to_update = f"{new_release}.g{current_commit}"
        msg = f"Downstream changes ({current_commit})"
        self.up.specfile.set_spec_version(
            release=release_to_update, changelog_entry=f"- {msg}"
        )

    def prepare_upstream_locally(
        self, version: str, commit: str, bump_version: bool, local_version: Optional[str]
    ) -> None:
        last_tag = self.up.get_last_tag()
        msg = ""
        if last_tag and bump_version:
            msg = self.up.get_commit_messages(after=last_tag)
        if not msg and bump_version:
            # no describe, no tag - just a boilerplate message w/ commit hash
            # or, there were no changes b/w HEAD and last_tag, which implies last_tag == HEAD
            msg = f"- Development snapshot ({commit})"
        release = self.up.get_spec_release(
            bump_version=bump_version,
            local_version=local_version,
        )
        logger.debug(f"Setting Release in spec to {release!r}.")
        # instead of changing version, we change Release field
        # upstream projects should take care of versions
        self.up.specfile.set_spec_version(
            version=version,
            release=release,
            changelog_entry=msg,
        )
