import inspect
import re
from logging import getLogger
from pathlib import Path
from typing import Union, List, Tuple

from rebasehelper.helpers.macro_helper import MacroHelper
from rebasehelper.specfile import SpecFile, RebaseHelperError

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
            logger.error(f"rebase-helper failed to change the spec file: {ex!r}")
            raise PackitException("rebase-helper didn't do the job")

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

    def add_patches(self, patch_list: List[Tuple[str, str]]) -> None:
        """
        Add the given list of (patch_name, msg) to the specfile.

        :param patch_list: [(patch_name, msg)]
        """
        if not patch_list:
            return

        logger.debug(f"About to add patches {patch_list} to specfile")
        with open(self.path, mode="r+") as spec_file:
            last_source_position = None
            line = spec_file.readline()
            while line:
                if line.startswith("Patch"):
                    raise PackitException(
                        "This specfile already contains patches, please remove them."
                    )
                if line.startswith("Source"):
                    last_source_position = spec_file.tell()
                line = spec_file.readline()

            if not last_source_position:
                raise PackitException(
                    "Cannot find a place to put patches in the specfile."
                )

            spec_file.seek(last_source_position)
            rest_of_the_file = spec_file.read()
            spec_file.seek(last_source_position)

            spec_file.write("\n# PATCHES FROM SOURCE GIT:\n")
            for i, (patch, msg) in enumerate(patch_list):
                commented_msg = "\n# " + "\n# ".join(msg.split("\n")) + "\n"
                spec_file.write(commented_msg)
                spec_file.write(f"Patch{(i+1):04d}: {patch}\n")

            spec_file.write("\n")
            spec_file.write(rest_of_the_file)

        logger.info(f"{len(patch_list)} patches added to {self.path}")
        # Since we write directly to file
        self.reload()

    def ensure_pnum(self, pnum: int = 1) -> None:
        """
        Make sure we use -p1 with %autosetup / %autopatch

        :param pnum: use other prefix number than default 1
        """
        logger.debug(f"Making sure we apply patches with -p{pnum}")
        prep_lines = self.spec_content.section("%prep")
        orig_lines = prep_lines.copy()

        for i, line in enumerate(prep_lines):
            if line.startswith(("%autosetup", "%autopatch")):
                if re.search(r"\s-p\d", line):
                    # -px is there, replace it with -p1
                    prep_lines[i] = re.sub(r"-p\d", rf"-p{pnum}", line)
                else:
                    # -px is not there, add -p1
                    prep_lines[i] = re.sub(
                        r"(%auto(setup|patch))", rf"\1 -p{pnum}", line
                    )
            elif line.startswith("%setup"):
                # %setup -> %autosetup -p1
                prep_lines[i] = line.replace("%setup", f"%autosetup -p{pnum}")
                # %autosetup does not accept -q, remove it
                prep_lines[i] = re.sub(r"\s+-q", r"", prep_lines[i])
            elif line.startswith("%patch"):
                # comment out old patch application macros
                prep_lines[i] = f"# {line}"
            if prep_lines[i] != line:
                logger.debug(f"{line!r} -> {prep_lines[i]!r}")

        if prep_lines != orig_lines:
            self.save()
