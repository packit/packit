# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import unittest
from pathlib import Path
from subprocess import CalledProcessError, check_output

from packit.api import PackitAPI
from packit.config import Config, get_package_config_from_repo
from packit.distgit import DistGit
from packit.exceptions import PackitException
from packit.local_project import LocalProject
from packit.upstream import Upstream
from requre.cassette import DataTypes
from requre.helpers.files import StoreFiles
from requre.helpers.simple_object import Simple
from requre.modules_decorate_all_methods import (
    record_git_module,
    record_requests_module,
    record_tempfile_module,
)
from requre.online_replacing import (
    apply_decorator_to_all_methods,
    replace_module_match,
)


@record_tempfile_module
@record_requests_module
@record_git_module
@apply_decorator_to_all_methods(
    replace_module_match(
        what="packit.utils.run_command_remote", decorate=Simple.decorator_plain()
    )
)
@apply_decorator_to_all_methods(
    replace_module_match(
        what="packit.pkgtool.PkgTool.clone",
        decorate=StoreFiles.where_arg_references(
            key_position_params_dict={"target_path": 2}
        ),
    )
)
@apply_decorator_to_all_methods(
    replace_module_match(
        what="copr.v3.helpers.config_from_file", decorate=Simple.decorator_plain()
    )
)
class ProposeUpdate(unittest.TestCase):
    def cassette_setup(self, cassette):
        cassette.data_miner.data_type = DataTypes.Dict

    def setUp(self):
        super().setUp()
        self.set_git_user()
        self._api = None
        self._static_tmp = None
        self._config = None
        self._project = None
        self._project_url = "https://github.com/packit/requre"
        self._project_specfile_path = Path("fedora", "python-requre.spec")
        self._pc = None
        self._dg = None
        self._lp = None
        self._upstream = None

    @staticmethod
    def set_git_user():
        try:
            check_output(["git", "config", "--global", "-l"])
        except CalledProcessError:
            check_output(
                ["git", "config", "--global", "user.email", "test@example.com"]
            )
            check_output(["git", "config", "--global", "user.name", "Tester"])

    @property
    def config(self):
        if not self._config:
            try:
                self._config = Config.get_user_config()
            except PackitException:
                self._config = Config()
        return self._config

    @property
    def project(self):
        if not self._project:
            self._project = self.config.get_project(url=self._project_url)
        return self._project

    @property
    def pc(self):
        if not self._pc:
            self._pc = get_package_config_from_repo(project=self.project)
        if not self._pc:
            raise RuntimeError("Package config not found.")
        return self._pc

    @property
    def dg(self):
        if not self._dg:
            self._dg = DistGit(self.config, self.pc)
        return self._dg

    @property
    def lp(self):
        if not self._lp:
            self._lp = LocalProject(git_project=self.project)
        return self._lp

    @property
    def upstream(self):
        if not self._upstream:
            self._upstream = Upstream(self.config, self.pc, local_project=self.lp)
        return self._upstream

    @property
    def api(self):
        if not self._api:
            self._api = PackitAPI(
                config=self.config,
                package_config=self.pc,
                upstream_local_project=self.lp,
            )
            self.api._up = self.upstream
            self.api._dg = self.dg
        return self._api

    @property
    def project_specfile_location(self):
        return self.lp.working_dir / self._project_specfile_path

    def check_version_increase(self):
        """Bump version in specfile and tag it with the new version.
        Might fail if such tag already exists in requre repo.
        In that case you probably need to bump Version in fedora/python-requre.spec
        """
        filedata = self.project_specfile_location.read_text()
        # Patch the specfile with new version
        version_increase = "0.0.0"
        for line in filedata.splitlines():
            if "Version:" in line:
                version = line.rsplit(" ", 1)[1]
                v1, v2, v3 = version.split(".")
                version_increase = ".".join([v1, str(int(v2) + 1), v3])
                filedata = filedata.replace(version, version_increase)
                break
        self.project_specfile_location.write_text(filedata)
        check_output(
            f"cd {self.lp.working_dir};"
            f"git commit -m 'test change' {self._project_specfile_path.name};"
            f"git tag -a {version_increase} -m 'my version {version_increase}'",
            shell=True,
        )
        self.api.sync_release(version="0.8.1", force=True)

    def test_comment_in_spec(self):
        """
        change specfile little bit to have there some change, do not increase version
        """
        with self.project_specfile_location.open("a") as myfile:
            myfile.write("\n# comment\n")
        version_increase = "10.0.0"
        check_output(
            f"cd {self.lp.working_dir};"
            f"git commit -m 'test change' {self._project_specfile_path};"
            f"git tag -a {version_increase} -m 'my version {version_increase}'",
            shell=True,
        )
        self.api.sync_release(version="0.8.1")

    def test_changelog_sync(self):
        """
        Bump version two times and see if the changelog is synced
        when it's configured to do so.
        """
        original_upstream_spec_content = self.api.up.absolute_specfile_path.read_text()
        check_output(
            f"cd {self.lp.working_dir};"
            f"rpmdev-bumpspec {self._project_specfile_path};"
            f"rpmdev-bumpspec {self._project_specfile_path};"
            f"git commit -m 'test change' {self._project_specfile_path}",
            shell=True,
        )
        changed_upstream_spec_content = self.api.up.absolute_specfile_path.read_text()
        assert original_upstream_spec_content != changed_upstream_spec_content
        self.api.package_config.sync_changelog = True
        self.api.sync_release(version="some.version", use_local_content=True)
        new_downstream_spec_content = self.api.dg.absolute_specfile_path.read_text()
        assert changed_upstream_spec_content == new_downstream_spec_content
