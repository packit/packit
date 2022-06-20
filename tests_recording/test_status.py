# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
from requre.cassette import DataTypes
from requre.helpers.files import StoreFiles
from requre.helpers.simple_object import Simple
from requre.modules_decorate_all_methods import (
    record_tempfile_module,
    record_git_module,
    record_requests_module,
)
from requre.online_replacing import (
    apply_decorator_to_all_methods,
    replace_module_match,
)

from packit.status import Status
from tests_recording.testbase import PackitTest


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
class TestStatus(PackitTest):
    def cassette_setup(self, cassette):
        cassette.data_miner.data_type = DataTypes.Dict

    def setUp(self):
        super().setUp()
        self._status = None

    @property
    def status(self):
        if not self._status:
            self._status = Status(self.config, self.pc, self.upstream, self.dg)
        return self._status

    def test_status(self):
        assert self.status

    def test_distgen_versions(self):
        table = self.status.get_dg_versions()
        assert table
        assert len(table) >= 3

    def test_koji_builds(self):
        table = self.status.get_koji_builds()
        assert table
        assert len(table) >= 2

    def test_copr_builds(self):
        table = self.status.get_copr_builds()
        assert table
        assert len(table) >= 2

    def test_up_releases(self):
        table = self.status.get_up_releases()
        assert len(table) >= 1

    def test_dowstream_pr(self):
        table = self.status.get_downstream_prs()
        assert len(table) >= 0
