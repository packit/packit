# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from requre.cassette import DataTypes
from requre.online_replacing import (
    record_requests_for_all_methods,
)

from packit.local_project import LocalProject
from tests_recording.testbase import PackitTest


@record_requests_for_all_methods()
class ProposeUpdate(PackitTest):
    def setUp(self):
        super().setUp()
        self._project_url = "https://github.com/packit/hello-world"

    def cassette_setup(self, cassette):
        cassette.data_miner.data_type = DataTypes.Dict

    def test_checkout_pr(self):
        """Test PR checkout with and without merging"""
        project = LocalProject(
            git_project=self.project,
            pr_id="596",
            git_url=self._project_url,
        )
        assert project.ref == "pr/596"

    def test_checkout_pr_no_merge(self):
        """Test PR checkout with and without merging"""
        project = LocalProject(
            git_project=self.project,
            pr_id="596",
            git_url=self._project_url,
            merge_pr=False,
        )
        assert project.ref == "pr/596"
