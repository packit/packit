import os
from typing import Optional

from rebasehelper.specfile import SpecFile

from packit.config import Config
from packit.local_project import LocalProject


class Upstream:
    """ interact with upstream project """
    def __init__(self, config: Config):
        self.config = config

        self._local_project = None
        self._specfile = None

        self.package_name: Optional[str] = self.config.package_config.metadata.get('package_name', None)
        self.upstream_project_url: str = self.config.package_config.upstream_project_url

    @property
    def specfile_path(self) -> Optional[str]:
        if self.package_name:
            return os.path.join(self.local_project.working_dir, f"{self.package_name}.spec")

    @property
    def local_project(self):
        """ return an instance of LocalProject """
        if self._local_project is None:
            self._local_project = LocalProject(
                working_dir=self.upstream_project_url
            )
        return self._local_project

    @property
    def specfile(self):
        if self._specfile is None:
            self._specfile = SpecFile(
                path=self.specfile_path,
                sources_location=self.local_project.working_dir,
                changelog_entry=None,
            )
        return self._specfile


class SourceGit(Upstream):
    pass
