import inspect

from rebasehelper.specfile import SpecFile

try:
    from rebasehelper.plugins.plugin_manager import plugin_manager
except ImportError:
    from rebasehelper.versioneer import versioneers_runner


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

    @staticmethod
    def _get_version(versioneer, package_name, category):
        try:
            get_version = plugin_manager.versioneers.run
        except NameError:
            get_version = versioneers_runner.run
        return get_version(versioneer, package_name, category)
