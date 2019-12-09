import inspect
import logging
import re

from rebasehelper.helpers.macro_helper import MacroHelper
from rebasehelper.specfile import SpecFile, RebaseHelperError

try:
    from rebasehelper.plugins.plugin_manager import plugin_manager
except ImportError:
    from rebasehelper.versioneer import versioneers_runner

from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


class Specfile(SpecFile):
    def __init__(self, path="", dir=None):
        s = inspect.signature(SpecFile)
        if "changelog_entry" in s.parameters:
            super().__init__(path=path, sources_location=str(dir), changelog_entry="")
        else:
            super().__init__(path=path, sources_location=str(dir))

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
