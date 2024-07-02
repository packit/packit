# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from subprocess import check_output

from bugzilla import Bugzilla
from flexmock import flexmock
from ogr.services.github.project import GithubProject
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

from packit.api import PackitAPI
from tests_recording.testbase import PackitTest


@record_tempfile_module
@record_requests_module
@record_git_module
@apply_decorator_to_all_methods(
    replace_module_match(
        what="packit.utils.run_command_remote",
        decorate=Simple.decorator_plain(),
    ),
)
@apply_decorator_to_all_methods(
    replace_module_match(
        what="packit.pkgtool.PkgTool.clone",
        decorate=StoreFiles.where_arg_references(
            key_position_params_dict={"target_path": 2},
        ),
    ),
)
@apply_decorator_to_all_methods(
    replace_module_match(
        what="copr.v3.helpers.config_from_file",
        decorate=Simple.decorator_plain(),
    ),
)
class ProposeUpdate(PackitTest):
    def cassette_setup(self, cassette):
        cassette.data_miner.data_type = DataTypes.Dict

    def setUp(self):
        super().setUp()
        self.configure_git()
        self._api = None

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
        self.api.sync_release(versions=["0.8.1"], force=True)

    # We don't run this test because we haven't been able to regenerate the data for it
    # and we're not sure what it's supposed to actually test.
    # https://github.com/packit/packit/issues/1726
    def comment_in_spec(self):
        """
        change specfile a bit to have there some change, do not increase version
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
        self.api.sync_release(versions=["0.8.1"])

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
            f"git commit --no-verify -m 'test change' {self._project_specfile_path}",
            shell=True,
        )
        changed_upstream_spec_content = self.api.up.absolute_specfile_path.read_text()
        assert original_upstream_spec_content != changed_upstream_spec_content
        # mock the release as there is no real release 0
        flexmock(GithubProject).should_receive("get_release").and_return(
            flexmock(url="url"),
        )
        # not able to record the bugzilla connection, therefore mocking
        flexmock(Bugzilla).should_receive("__init__")
        flexmock(Bugzilla).should_receive("query").and_return([])

        self.api.package_config.sync_changelog = True
        self.api.sync_release(versions=["1.0.0"], use_local_content=True)
        new_downstream_spec_content = self.api.dg.absolute_specfile_path.read_text()
        assert changed_upstream_spec_content == new_downstream_spec_content
