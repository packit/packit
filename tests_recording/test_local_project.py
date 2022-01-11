# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from requre.cassette import DataTypes
from requre.modules_decorate_all_methods import (
    record_tempfile_module,
    # record_git_module,
    record_requests_module,
)

from packit.local_project import LocalProject
from tests_recording.testbase import PackitTest

PR_ID = "227"


@record_tempfile_module()
@record_requests_module
# @record_git_module()  # https://github.com/packit/requre/issues/232
class TestLocalProject(PackitTest):
    """Test LocalProject and save interaction with GitHub"""

    def cassette_setup(self, cassette):
        """requre requires this method to be present"""
        cassette.data_miner.data_type = DataTypes.Dict

    @staticmethod
    def commit_title(lp: LocalProject):
        commit_msg = lp.git_repo.head.commit.message
        return commit_msg.split("\n", 1)[0]

    def test_checkout_pr(self):
        """Test PR checkout with and without merging"""
        project = LocalProject(
            git_project=self.project,
            pr_id=PR_ID,
            git_url=self._project_url,
            working_dir=self.static_tmp,
        )
        assert project.ref == f"pr/{PR_ID}"
        assert (
            self.commit_title(project)
            == "Merge pull request #227 from lachmanfrantisek/koji-builds"
        )
        assert "koji_build" in (project.working_dir / ".packit.yaml").read_text()

    def test_checkout_pr_no_merge(self):
        """Test PR checkout with and without merging"""
        project = LocalProject(
            git_project=self.project,
            pr_id=PR_ID,
            git_url=self._project_url,
            working_dir=self.static_tmp,
            merge_pr=False,
        )
        assert project.ref == f"pr/{PR_ID}"
        assert (
            self.commit_title(project)
            == "Run Koji builds automatically for new dist-git commits"
        )
        assert "koji_build" in (project.working_dir / ".packit.yaml").read_text()
