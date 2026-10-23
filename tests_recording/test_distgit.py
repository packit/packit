# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Tests for the DistGit class
"""

import json
from pathlib import Path

from git import Repo
from requre.helpers.httpx_response import record_httpx
from requre.modules_decorate_all_methods import (
    record_git_module,
    record_tempfile_module,
)

from packit.config import Config, PackageConfig, get_package_config_from_repo
from packit.distgit import DistGit
from packit.local_project import LocalProject
from tests_recording.testbase import PackitTest

CONFIG_YAML = """
{
    "upstream_project_url": "https://github.com/packit/requre",
    "upstream_package_name": "requre",
    "downstream_package_name": "python-requre",
    "dist_git_base_url": "https://forgejo-src.stg.fedoraproject.org",
    "dist_git_namespace": "rpms",
    "packages": {
        "python-requre": {
            "specfile_path": "python-requre.spec"
        }
    },
    "jobs": []
}
"""


@record_tempfile_module
@record_httpx
@record_git_module
class TestDistGit(PackitTest):
    """
    A class of integration tests covering various interactions of packit
    with Forgejo dist-git. These tests interact with the rpms/python-requre
    package and its fork.
    """

    def _prepare_local_dg_clone(self):
        """
        Clones the rpms/python-requre package from dist-git and creates
        an instance of DistGit based on this local clone.
        """
        packages_config_dict = json.loads(CONFIG_YAML)
        packages_config = PackageConfig.get_from_dict(packages_config_dict)

        distgit_base_url = packages_config.dist_git_base_url
        distgit_namespace = packages_config.dist_git_namespace
        distgit_repo_name = packages_config.downstream_package_name
        distgit_full_repo_name = f"{distgit_namespace}/{distgit_repo_name}"
        distgit_clone_url = f"{distgit_base_url}{distgit_full_repo_name}"

        # temporary working directory to clone into
        tmp_path = Path(self.static_tmp)
        self.tmp_repo = tmp_path / "requre"

        # clone rpms/python-requre into temporary the working directory
        self.repo = Repo.clone_from(url=distgit_clone_url, to_path=str(self.tmp_repo))
        self.configure_git()

        # instantiate LocalProject from the temporary working directory
        local_project = LocalProject(
            working_dir=self.tmp_repo,
            ref="rawhide",
            git_url="",
            full_name=distgit_full_repo_name,
            namespace=distgit_namespace,
            repo_name=distgit_repo_name,
            remote="",
            git_service=self.dg_service,
            git_project=self.dg_project,
        )

        # instantiate the DistGit class using the package configuration
        # defined in CONFIG_YAML
        return DistGit(
            config=Config(),
            package_config=packages_config,
            local_project=local_project,
        )

    def _make_dummy_commit(self, distgit, commit_title, commit_msg):
        """
        Make an arbitrary change in the README.md file and create a local commit.
        The change in the README.md file is done only so that there is something
        to commit.
        """

        with open(self.tmp_repo / "README.md", "a") as f:
            f.write("\nThe bogeyman played with this file.\n")

        # create a commit in the current (local) branch
        distgit.commit(
            title=commit_title,
            msg=commit_msg,
        )

    def test_basic_distgit_workflow(self):
        """
        Tests cloning from DistGit, pushing changes to a new branch
        in a remote fork and creating a pull request against the original
        python-requre repo in the rpms namespace.

        This test doesn't do a force push to the fork's branch, so make sure
        this branch doesn't exist on the fork before re-recording.
        """

        testing_branch = "my-testing-branch"
        distgit = self._prepare_local_dg_clone()

        # create a local branch, checkout to it and create a commit
        distgit.create_branch(testing_branch)
        distgit.switch_branch(testing_branch)

        commit_title = "My testing commit"
        commit_msg = "I am losing my mind"
        self._make_dummy_commit(distgit, commit_title, commit_msg)

        # push the testing branch to a remote fork
        distgit.push_to_fork(
            branch_name=testing_branch,
        )

        # create a pull request from the fork to the original repo's
        # rawhide branch in rpms/python-requre
        pr = distgit.create_pull(
            pr_title="DistGit testing PR",
            pr_description="This might not work",
            source_branch=testing_branch,
            target_branch="rawhide",
        )

        assert pr
        assert pr.title == "DistGit testing PR"
        assert pr.target_branch == "rawhide"
        assert pr.source_branch == testing_branch
        assert pr.target_project.namespace == "rpms"

        pr.comment("Test whether commenting works")
        assert len(list(pr.get_comments())) > 0

    def test_rebase_distgit_branch(self):
        """
        Tests creating a new branch in dist-git, and rebasing it
        onto a different branch.

        The first push to the branch is not a force push, so make sure
        this branch doesn't exist on the fork before re-recording.
        """
        testing_branch = "testing-rebase-branch"
        distgit = self._prepare_local_dg_clone()

        distgit.checkout_branch("f43")
        distgit.create_branch(testing_branch)
        distgit.switch_branch(testing_branch)

        # create a commit on this branch before rebasing
        # then check that the commit survives the rebase
        commit_title = "A random commit"
        commit_msg = "Nothing to add here"
        self._make_dummy_commit(distgit, commit_title, commit_msg)

        distgit.push_to_fork(testing_branch)

        head = distgit.local_project.git_repo.head.commit
        f43_tip = distgit.local_project.git_repo.commit("origin/f43")

        assert head.summary == "[packit] A random commit"
        assert head.parents[0].hexsha == f43_tip.hexsha

        distgit.rebase_branch(onto_branch="rawhide")

        distgit.push_to_fork(testing_branch, force=True)

        head = distgit.local_project.git_repo.head.commit
        rawhide_tip = distgit.local_project.git_repo.commit("origin/rawhide")

        assert head.summary == "[packit] A random commit"
        assert head.parents[0].hexsha == rawhide_tip.hexsha

    def _assert_package_config_matches_expectation(self, ref):
        """
        Fetches the package configuration file (.packit.yaml) from a remote
        project fork based on a specified ref and asserts that the file
        was successfully fetched and that its content matches expectation.
        """
        package_config = get_package_config_from_repo(
            project=self.dg_project_fork,
            ref=ref,
        )
        assert package_config

        # only the requre package should be defined in the config file
        package_config_views = package_config.get_package_config_views()
        assert len(package_config_views) == 1

        requre_config = package_config_views["python-requre"]
        assert requre_config.upstream_package_name == "requre"
        assert requre_config.downstream_package_name == "python-requre"
        assert requre_config.specfile_path == "fedora/python-requre.spec"

        # check jobs defined for the requre package
        job_views = package_config.get_job_views()

        expected_jobs = {
            ("copr_build", "pull_request"),
            ("copr_build", "commit"),
            ("copr_build", "release"),
            ("tests", "pull_request"),
            ("propose_downstream", "release"),
            ("koji_build", "commit"),
            ("bodhi_update", "commit"),
        }
        actual_jobs = {
            (job_view.type.value, job_view.trigger.value) for job_view in job_views
        }
        assert expected_jobs == actual_jobs

    def test_get_package_config_from_repo_branch(self):
        """
        Tests whether Packit is able to fetch the package configuration
        file from the specified branch on a remote fork.
        """
        ref = "refs/heads/f45"
        self._assert_package_config_matches_expectation(ref)

    def test_get_package_config_from_repo_pull_request(self):
        """
        Tests whether Packit is able to fetch the package configuration
        file from the HEAD commit of the specified pull request on a remote fork.
        """
        ref = "refs/pull/1/head"
        self._assert_package_config_matches_expectation(ref)

    def test_get_package_config_from_repo_tag(self):
        """
        Tests whether Packit is able to fetch the package configuration
        file from a remote fork's tagged commit.
        """
        ref = "refs/tags/my-testing-tag"
        self._assert_package_config_matches_expectation(ref)

    def test_get_package_config_from_repo_commit(self):
        """
        Tests whether Packit is able to fetch the package configuration
        file from a remote fork's commit based on its sha.
        """
        ref = "a350f973f96ae1872fb97072d11adcc2881cbea1"
        self._assert_package_config_matches_expectation(ref)
