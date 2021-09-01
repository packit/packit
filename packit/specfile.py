# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import inspect
import re
from logging import getLogger
from pathlib import Path
from typing import Union, List, Optional, Dict

from packit.patches import PatchMetadata
from rebasehelper.helpers.macro_helper import MacroHelper
from rebasehelper.specfile import SpecFile, RebaseHelperError, saves, PatchObject
from rebasehelper.tags import Tag, Tags

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
        self._patch_id_digits: Optional[int] = None
        self._uses_autosetup: Optional[bool] = None

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
                # using set_tag instead of set_version to turn off preserving macros
                self.set_tag("Version", version, preserve_macros=False)

            if release:
                # using set_tag instead of set_release to turn off preserving macros
                self.set_tag(
                    "Release", "{}%{{?dist}}".format(release), preserve_macros=False
                )

            if not changelog_entry:
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
    def set_patches(
        self, patch_list: List[PatchMetadata], patch_id_digits: int = 4
    ) -> None:
        """
        Set given patches in the spec file

        :param patch_list: [PatchMetadata]
        :param patch_id_digits: Number of digits of the generated patch ID.
            This is used to control whether to have 'Patch' or 'Patch1' or 'Patch0001'.
        """
        if not patch_list:
            return

        if all(p.present_in_specfile for p in patch_list):
            logger.debug(
                "All patches are present in the spec file, nothing to do here 🚀"
            )
            return

        # we could have generated patches before (via git-format-patch)
        # so let's reload the spec
        self.reload()

        applied_patches: Dict[str, PatchObject] = {
            p.get_patch_name(): p for p in self.get_applied_patches()
        }

        for patch_metadata in patch_list:
            if patch_metadata.present_in_specfile:
                logger.debug(
                    f"Patch {patch_metadata.name} is already present in the spec file."
                )
                continue

            if patch_metadata.name in applied_patches:
                logger.debug(
                    f"Patch {patch_metadata.name} is already defined in the spec file."
                )
                continue

            self.add_patch(patch_metadata, patch_id_digits)

    def add_patch(
        self, patch_metadata: PatchMetadata, patch_id_digits: Optional[int] = 4
    ):
        """
        Add provided patch to the spec file:
         * Set Patch index to be +1 than the highest index of an existing specfile patch
         * The Patch placement logic works like this:
           * If there already are patches, then the patch is added after them
           * If there are no existing patches, the patch is added after Source definitions

        Args:
            patch_metadata: Metadata of the patch to be added.
            patch_id_digits: Number of digits of the generated patch ID. This is used to
                control whether to have 'Patch' or 'Patch1' or 'Patch0001'.
        """
        try:
            patch_number_offset = max(x.index for x in self.get_applied_patches())
        except ValueError:
            logger.debug("There are no patches in the spec.")
            # 0 is a valid patch index
            patch_number_offset = -1

        if patch_metadata.patch_id is not None:
            if patch_metadata.patch_id <= patch_number_offset:
                raise PackitException(
                    f"The 'patch_id' requested ({patch_metadata.patch_id}) for patch "
                    f"{patch_metadata.name} is less than or equal to the last used patch ID "
                    f"({patch_number_offset}). Re-ordering the patches using 'patch_id' is "
                    "not allowed - if you want to change the order of those patches, "
                    "please reorder the commits in your source-git repository."
                )
            patch_id = patch_metadata.patch_id
        else:
            # 0 is a valid patch index, but let's start with 1 which is more common, e.g.
            # https://src.fedoraproject.org/rpms/glibc/blob/f6682c9bac5872385b3caae0cd51fe3dbfcbb88f/f/glibc.spec#_158
            # https://src.fedoraproject.org/rpms/python3.10/blob/ac9a5093cb9f534ef2f65cbd1f50684c88b91eec/f/python3.10.spec#_267
            patch_id = max(patch_number_offset + 1, 1)

        new_content = "\n"
        new_content += "\n".join(
            line if line.startswith("#") else f"# {line}".strip()
            for line in patch_metadata.specfile_comment.splitlines()
        )
        patch_id_str = f"{patch_id:0{patch_id_digits}d}" if patch_id_digits > 0 else ""
        new_content += f"\nPatch{patch_id_str}: {patch_metadata.name}"

        if self.get_applied_patches():
            last_source_tag_line = [
                t.line for t in self.tags.filter(name="Patch*", valid=None)
            ][-1]
        else:
            last_source_tag_line = [
                t.line for t in self.tags.filter(name="Source*", valid=None)
            ][-1]

        # Find first empty line after last_source_tag_line
        for index, line in enumerate(
            self.spec_content.section("%package")[last_source_tag_line:],
            start=last_source_tag_line,
        ):
            if not line:
                where = index
                break
        else:
            where = len(self.spec_content.section("%package"))

        logger.debug(f"Adding patch {patch_metadata.name} to the spec file.")
        self.spec_content.section("%package")[where:where] = new_content.splitlines()
        self.save()

    def get_source(self, source_name: str) -> Optional[Tag]:
        """
        get specific Source from spec

        :param source_name: precise name of the Source, e.g. Source1, or Source
        :return: corresponding Source Tag
        """
        # sanitize the name, this will also add index if there isn't one
        source_name, *_ = Tags._sanitize_tag(source_name, 0, 0)
        return next(self.tags.filter(name=source_name, valid=None), None)

    def read_patch_comments(self) -> dict:
        """Read the spec again, detect comment lines right above a patch-line
        and save it as an attribute to the patch for later retrieval.

        Match patch-lines with the patch-data from rebase-helper on the name of
        the patches.

        Returns:
            A dict where each patch name (the basename of the value of the
            patch-line) has 0 or more comment lines associated with it.
        """
        comment: List[str] = []
        patch_comments = {}
        for line in self.spec_content.section("%package"):
            # An empty line clears the comment lines collected so far.
            if not line.strip():
                comment = []
            # Remember a comment line.
            if line.startswith("#"):
                comment.append(line[1:].strip())
            # Associate comments with patches and clear the comments
            # collected.
            if line.lower().startswith("patch"):
                patch_name = Path(line.split(":", 1)[1].strip()).name
                patch_comments[patch_name] = comment
                comment = []
        return patch_comments

    @property
    def patch_id_digits(self) -> int:
        """Detect and return the number of digits used in patch IDs (indices).

        Look for the first patch-line, and use that as a reference.

        0 - no patch ID at all, just a bare "Patch"
        1 - no leading zeros for patch IDs
        2 or more - the minimum number of digits to be used for patch IDs.

        Returns:
            Number of digits used on the first patch-line, or 0 if there is
            no patch-line found.
        """
        if self._patch_id_digits is not None:
            return self._patch_id_digits

        self._patch_id_digits = 1
        for line in self.spec_content.section("%package"):
            if line.lower().startswith("patch"):
                match = re.match(r"^patch(\d*)\s*:.+", line, flags=re.IGNORECASE)
                if not match[1]:
                    self._patch_id_digits = 0
                elif match[1].startswith("0"):
                    self._patch_id_digits = len(match[1])
                break

        return self._patch_id_digits

    @property
    def uses_autosetup(self) -> bool:
        """Tell if the specfile uses %autosetup

        Returns:
            True if the file uses %autosetup, otherwise False.
        """

        if self._uses_autosetup is not None:
            return self._uses_autosetup

        self._uses_autosetup = False
        for line in self.spec_content.section("%prep"):
            if line.startswith("%autosetup"):
                self._uses_autosetup = True
                break

        return self._uses_autosetup

    def remove_patches(self):
        """Remove all patch-lines from the spec file"""
        content = []
        stretch = []
        for line in self.spec_content.section("%package"):
            stretch.append(line)
            # Empty lines save the current stretch into content.
            if not line.strip():
                content += stretch
                stretch = []
            # Patch-lines throw away the current stretch.
            if line.lower().startswith("patch"):
                stretch = []
                # If there is an empty line at the end of content
                # throw it away, to avoid duplicate lines.
                if not content[-1].strip():
                    content.pop()
        self.spec_content.replace_section("%package", content)
        self.save()
