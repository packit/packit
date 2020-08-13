# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import inspect
import re
from logging import getLogger
from pathlib import Path
from typing import Union, List, Tuple, Optional

from rebasehelper.helpers.macro_helper import MacroHelper
from rebasehelper.specfile import SpecFile, RebaseHelperError, saves

from packit.constants import SPEC_PACKAGE_SECTION
from packit.patches import PatchMetadata

try:
    from rebasehelper.plugins.plugin_manager import plugin_manager
except ImportError:
    from rebasehelper.versioneer import versioneers_runner

from packit.exceptions import PackitException

logger = getLogger(__name__)


class Specfile(SpecFile):
    def __init__(self, path: Union[str, Path], sources_dir: Union[str, Path] = ""):
        s = inspect.signature(SpecFile)
        if "changelog_entry" in s.parameters:
            super().__init__(
                path=str(path), sources_location=str(sources_dir), changelog_entry=""
            )
        else:
            super().__init__(path=str(path), sources_location=str(sources_dir))

    def update_spec(self):
        if hasattr(self, "update"):
            # new rebase-helper
            self.update()
        else:
            # old rebase-helper
            self._update_data()

    def update_changelog_in_spec(self, changelog_entry):
        if hasattr(self, "update_changelog"):
            # new rebase-helper
            self.update_changelog(changelog_entry)
        else:
            # old rebase-helper
            self.changelog_entry = changelog_entry
            new_log = self.get_new_log()
            new_log.extend(self.spec_content.sections["%changelog"])
            self.spec_content.sections["%changelog"] = new_log
            self.save()

    def set_spec_version(
        self, version: str = None, release: str = None, changelog_entry: str = None
    ):
        """
        Set version in spec, release and add a changelog_entry (if they are presented).

        :param version: new version
        :param release: new release
        :param changelog_entry: accompanying changelog entry
        """
        try:
            if version:
                # also this code adds 3 rpmbuild dirs into the upstream repo,
                # we should ask rebase-helper not to do that
                self.set_version(version=version)

            if release:
                self.set_release_number(release=release)

            if not changelog_entry:
                return

            if not self.spec_content.section("%changelog"):
                logger.debug(
                    "The specfile doesn't have any %changelog, will not set it."
                )
                return

            self.update_changelog_in_spec(changelog_entry)

        except RebaseHelperError as ex:
            logger.error(f"Rebase-helper failed to change the spec file: {ex}")
            raise PackitException("Rebase-helper didn't do the job.")

    def write_spec_content(self):
        if hasattr(self, "_write_spec_content"):
            # new rebase-helper
            self._write_spec_content()
        else:
            # old rebase-helper
            self._write_spec_file_to_disc()

    @staticmethod
    def get_upstream_version(versioneer, package_name, category):
        """
        Call the method of rebase-helper (due to the version of rebase-helper)
        to get the latest upstream version of a package.
        :param versioneer:
        :param package_name: str
        :param category:
        :return: str version
        """
        try:
            get_version = plugin_manager.versioneers.run
        except NameError:
            get_version = versioneers_runner.run
        return get_version(versioneer, package_name, category)

    def get_release_number(self) -> str:
        """
        Removed in rebasehelper=0.20.0
        """
        release = self.header.release
        dist = MacroHelper.expand("%{dist}")
        if dist:
            release = release.replace(dist, "")
        return re.sub(r"([0-9.]*[0-9]+).*", r"\1", release)

    @saves
    def remove_applied_patches(self) -> None:
        """
        In prep section comment out all lines starting with %patch
        """
        indexes = [p.index for p in self.get_applied_patches()]
        if indexes:
            logger.debug("About to remove all %patch from %prep.")
            self._process_patches(comment_out=indexes)

    @saves
    def add_patches(self, patch_list: List[PatchMetadata]) -> None:
        """
        Add given patches to the specfile.

        :param patch_list: [PatchMetadata]
        """
        if not patch_list:
            return

        if all(p.present_in_specfile for p in patch_list):
            logger.debug(
                "All patches are present in the spec file, nothing to do here 🚀"
            )
            return

        logger.debug(f"About to add patches {patch_list} to specfile.")
        if [t.name for t in self.tags.filter(name="Patch*")]:
            logger.debug("This specfile already contains patches.")

        source_git_patches: List[PatchMetadata] = []
        original_patches: List[PatchMetadata] = []
        for patch in patch_list:
            if patch.present_in_specfile:
                original_patches.append(patch)
            else:
                source_git_patches.append(patch)

        logger.debug(
            f"Original patches ({len(original_patches)}) "
            "has to be already in the spec-file. "
            "Following patches will not be added to the spec-file:\n - "
            + "\n - ".join(f"{patch.name} ({patch.path})" for patch in original_patches)
            + "\n"
        )

        logger.debug(f"Adding source-git patches ({len(source_git_patches)})")
        new_content = "\n# PATCHES FROM SOURCE GIT:\n"
        for i, patch_metadata in enumerate(source_git_patches):
            new_content += "\n# " + "\n# ".join(
                patch_metadata.specfile_comment.split("\n")
            )
            new_content += f"\nPatch{(i + 1):04d}: {patch_metadata.name}\n"

        # valid=None: take any SourceX even if it's disabled
        last_source_tag_line = [
            t.line for t in self.tags.filter(name="Source*", valid=None)
        ][-1]
        # find the first empty line after last_source_tag
        for i, line in enumerate(
            self.spec_content.section("%package")[last_source_tag_line:]
        ):
            if line.strip() == "":
                break
        else:
            logger.error("Can't find where to add patches.")
            return
        where = last_source_tag_line + i
        # insert new content below last Source
        self.spec_content.section("%package")[where:where] = new_content.split("\n")

        logger.info(f"{len(patch_list)} patches added to {self.path!r}.")

    def get_source(self, source_name: str) -> Optional[Tuple[int, str, str]]:
        """
        get specific Source from spec

        :param source_name: precise name of the Source, e.g. Source1, or Source
        :return: index within the section, real name of the source, whole source line
        """
        prefix = "Source"
        self.get_main_source()
        regex = re.compile(r"^Source\s*:.+$")
        spec_section = self.spec_content.section(SPEC_PACKAGE_SECTION)
        for idx, line in enumerate(spec_section):
            # we are looking for Source lines
            if line.startswith(prefix):
                # it's a Source line!
                if line.startswith(source_name):
                    # it even matches the specific Source\d+
                    full_name = source_name
                elif regex.match(line):
                    # okay, let's try the other very common default
                    # https://github.com/packit/packit/issues/536#issuecomment-534074925
                    full_name = prefix
                else:
                    # nope, let's continue the search
                    continue
                return idx, full_name, line
        return None
