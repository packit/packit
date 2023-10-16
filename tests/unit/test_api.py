# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pathlib
from contextlib import suppress as does_not_raise

import pytest
from flexmock import flexmock
from munch import Munch

from packit import api as packit_api
from packit.api import PackitAPI
from packit.config import CommonPackageConfig, PackageConfig, RunCommandType
from packit.config.config import Config
from packit.copr_helper import CoprHelper
from packit.distgit import DistGit
from packit.exceptions import PackitException
from packit.local_project import LocalProjectBuilder
from packit.patches import PatchGenerator
from packit.sync import SyncFilesItem
from packit.utils.changelog_helper import ChangelogHelper


def build_dict(copr_url, id):
    """Create a build object which uses 'copr_url' and 'id'."""
    # copr_client.build_proxy.get(build_id) response
    return Munch(
        {
            "chroots": [
                "fedora-29-x86_64",
                "fedora-30-x86_64",
                "fedora-rawhide-x86_64",
            ],
            "ended_on": 1566377991,
            "id": str(id),
            "ownername": "packit",
            "project_dirname": "packit-service-ogr-160",
            "projectname": "packit-service-ogr-160",
            "repo_url": f"{copr_url}/results/packit/packit-service-ogr-160",
            "source_package": {
                "name": "python-ogr",
                "url": "https://copr-be.cloud.fedoraproject.org/results/"
                "packit/packit-service-ogr-160/srpm-builds/01010428/"
                "python-ogr-0.6.1.dev51ge88ac83-1.fc30.src.rpm",
                "version": "0.6.1.dev51+ge88ac83-1.fc30",
            },
            "started_on": 1566377844,
            "state": "succeeded",
            "submitted_on": 1566377764,
            "submitter": "packit",
        },
    )


def copr_helper(copr_url):
    """Create a mock CoprHelper, with a copr_client configured with 'copr_url'."""
    helper = CoprHelper(flexmock())
    helper._copr_client = flexmock(config={"copr_url": copr_url})
    return helper


testdata = [
    pytest.param(
        copr_helper("https://supr.copr"),
        build_dict("https://supr.copr", 1010428),
        "https://supr.copr/coprs/build/1010428/",
        id="user",
    ),
    # The name "group" bellow is kept for historical reasons.
    # These Copr permalinks have no information in them regarding who
    # the owner of the build is (although they will have, once they redirect).
    pytest.param(
        copr_helper("https://group.copr"),
        build_dict("https://group.copr", 1010430),
        "https://group.copr/coprs/build/1010430/",
        id="group",
    ),
]


@pytest.fixture
def api_mock(config_mock, package_config_mock, upstream_mock, distgit_mock):
    api = PackitAPI(config=config_mock, package_config=package_config_mock)
    flexmock(api)
    api._up = upstream_mock
    api._dg = distgit_mock
    api.should_receive("_prepare_files_to_sync").and_return([])
    api.should_receive("_handle_sources")
    api.should_receive("_get_sandcastle_exec_dir").and_return("sandcastle-exec-dir")
    return api


@pytest.mark.parametrize(
    "helper,build,web_url",
    testdata,
)
class TestPackitAPI:
    def test_copr_web_build_url(self, helper, build, web_url):
        assert helper.copr_web_build_url(build) == web_url


@pytest.mark.parametrize(
    "version, tag, get_latest_released_return, get_specfile_version_return, expectation",
    [
        pytest.param(
            "1.1.1",
            None,
            None,
            "0",
            does_not_raise(),
            id="version_set(CLI_explicit)",
        ),
        pytest.param(
            None,
            "v1.1.1",
            None,
            "0",
            does_not_raise(),
            id="tag_set(service_mode)",
        ),
        pytest.param(
            "1.1",
            "v1.1.1",
            None,
            None,
            pytest.raises(PackitException),
            id="both_set(CLI_wrong_usage)",
        ),
        pytest.param(
            None,
            None,
            "1.1",
            "0",
            does_not_raise(),
            id="none_set(CLI_version_from_upstream_release_monitoring)",
        ),
        pytest.param(
            None,
            None,
            None,
            None,
            pytest.raises(PackitException),
            id="none_set(CLI_version_not_in_upstream_release_monitoring)",
        ),
    ],
)
def test_sync_release_version_tag_processing(
    version,
    tag,
    get_latest_released_return,
    get_specfile_version_return,
    expectation,
    api_mock,
):
    api_mock.up.package_config.upstream_tag_template = "v{version}"
    api_mock.up.should_receive("get_latest_released_version").and_return(
        get_latest_released_return,
    )
    api_mock.up.should_receive("get_specfile_version").and_return(
        get_specfile_version_return,
    )
    api_mock.up.should_receive("specfile").and_return(
        flexmock().should_receive("reload").mock(),
    )
    api_mock.up.package_config.should_receive("get_package_names_as_env").and_return({})
    api_mock.should_receive("_prepare_files_to_sync").with_args(
        synced_files=[],
        full_version=version,
        upstream_tag=tag,
    )
    api_mock.should_receive("push_and_create_pr").and_return(flexmock())
    flexmock(PatchGenerator).should_receive("undo_identical")
    with expectation:
        api_mock.sync_release(version=version, tag=tag, dist_git_branch="_")


def test_sync_release_do_not_create_sync_note(api_mock):
    flexmock(PatchGenerator).should_receive("undo_identical")
    flexmock(pathlib.Path).should_receive("write_text").never()
    api_mock.up.should_receive("get_specfile_version").and_return("0")
    api_mock.up.should_receive("specfile").and_return(
        flexmock().should_receive("reload").mock(),
    )
    api_mock.up.package_config.should_receive("get_package_names_as_env").and_return({})
    api_mock.up.package_config.create_sync_note = False
    api_mock.should_receive("push_and_create_pr").and_return(flexmock())
    api_mock.sync_release(version="1.1", dist_git_branch="_")


def test_sync_release_create_sync_note(api_mock):
    flexmock(PatchGenerator).should_receive("undo_identical")
    flexmock(pathlib.Path).should_receive("write_text").once()
    api_mock.up.should_receive("get_specfile_version").and_return("0")
    api_mock.up.should_receive("specfile").and_return(
        flexmock().should_receive("reload").mock(),
    )
    api_mock.up.package_config.should_receive("get_package_names_as_env").and_return({})
    api_mock.should_receive("push_and_create_pr").and_return(flexmock())
    api_mock.sync_release(version="1.1", dist_git_branch="_")


def test_sync_release_env(api_mock):
    env = api_mock.sync_release_env
    assert env == {
        "PACKIT_DOWNSTREAM_REPO": "/mock_dir/sandcastle/dist-git",
        "PACKIT_UPSTREAM_REPO": "/mock_dir/sandcastle/local-project",
    }
    api_mock.config.command_handler = RunCommandType.sandcastle
    env = api_mock.sync_release_env
    assert env == {
        "PACKIT_DOWNSTREAM_REPO": "/mock_dir/sandcastle/sandcastle-exec-dir/dist-git",
        "PACKIT_UPSTREAM_REPO": "/mock_dir/sandcastle/sandcastle-exec-dir/local-project",
    }


@pytest.mark.parametrize(
    "path, downstream_package_name, expectation",
    [
        pytest.param("/systemd", "systemd", "systemd", id="both_set"),
        pytest.param(None, "systemd", "systemd", id="both_set"),
        pytest.param("/systemd", None, "systemd", id="both_set"),
        pytest.param(None, None, None, id="none_set"),
    ],
)
def test_dg_downstream_package_name_is_set(
    api_mock,
    path,
    downstream_package_name,
    expectation,
):
    api_mock._dg = None
    api_mock.package_config.downstream_package_name = downstream_package_name
    api_mock.downstream_local_project = LocalProjectBuilder().build(working_dir=path)
    assert api_mock.dg.package_config.downstream_package_name == expectation


def test_sync_release_sync_files_call(config_mock, upstream_mock, distgit_mock):
    pc = PackageConfig(
        packages={
            "package": CommonPackageConfig(
                specfile_path="xxx",
                files_to_sync=[
                    SyncFilesItem(
                        ["src/a"],
                        "dest",
                        filters=["dummy filter"],
                        mkpath=True,
                        delete=True,
                    ),
                ],
                upstream_package_name="test_package_name",
                downstream_package_name="test_package_name",
                upstream_tag_template="_",
                upstream_project_url="_",
                upstream_ref="_",
            ),
        },
    )
    upstream_mock.package_config = pc
    distgit_mock.package_config = pc
    api = PackitAPI(config=config_mock, package_config=pc)
    flexmock(api)
    api._up = upstream_mock
    api._dg = distgit_mock
    api.should_receive("_handle_sources")
    flexmock(PatchGenerator).should_receive("undo_identical")
    flexmock(pathlib.Path).should_receive("write_text").once()
    api.up.should_receive("get_specfile_version").and_return("0")
    api.up.should_receive("specfile").and_return(
        flexmock().should_receive("reload").mock(),
    )
    api.should_receive("push_and_create_pr").and_return(flexmock())
    flexmock(ChangelogHelper).should_receive("update_dist_git")

    flexmock(packit_api).should_receive("sync_files").with_args(
        [
            SyncFilesItem(
                src=["/mock_dir/sandcastle/local-project/src/a"],
                dest="/mock_dir/sandcastle/dist-git/dest",
                mkpath=True,
                delete=True,
                filters=["dummy filter"],
            ),
        ],
    )

    api.sync_release(version="1.1", dist_git_branch="_")


def test_sync_release_check_pr_instructions(api_mock):
    flexmock(PatchGenerator).should_receive("undo_identical")
    api_mock.up.should_receive("get_specfile_version").and_return("0")
    api_mock.up.should_receive("specfile").and_return(
        flexmock().should_receive("reload").mock(),
    )
    api_mock.up.package_config.should_receive("get_package_names_as_env").and_return({})
    api_mock.should_receive("push_and_create_pr").with_args(
        pr_title=str,
        pr_description=(
            "Upstream tag: _\nUpstream commit: _\n\n---\n\n"
            "If you need to do any change in this pull request, you can clone Packit's fork "
            "and push directly to the source branch of this PR (provided you have commit access "
            "to this repository):\n"
            "```\n"
            "git clone ssh://$YOUR_USER@pkgs.fedoraproject.org/forks/packit/rpms/package.git\n"
            "cd package\n"
            "git checkout 1.1-_-update\n"
            "```\n"
            "\n---\n\n"
            "Alternatively, you can locally fetch the source branch of this PR "
            "from Packit's fork and push it (with a fix) to your fork:\n"
            "```\n"
            "git fetch https://src.fedoraproject.org/forks/packit/rpms/package.git "
            "refs/heads/*:refs/remotes/packit/*\n"
            "git checkout packit/1.1-_-update\n"
            "```\n"
            "If you have the `koji_build` job configured as well, make sure to configure "
            "the `allowed_pr_authors` and/or `allowed_committers` (see [the docs]"
            "(https://packit.dev/docs/configuration/downstream/koji_build#optional-parameters)) "
            "since by default, Packit reacts only to its own PRs.\n"
            "\n---\n\n"
            "Before pushing builds/updates, please remember to check the new "
            "version against the "
            "[packaging guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/).\n\n"
            "For example, please:\n\n"
            "- check that the new sources only contain permissible content\n"
            "- check that the license of the new version has not changed\n"
            "- check for any API/ABI and other changes that may break dependent packages\n"
            "- check the autogenerated changelog\n"
        ),
        git_branch=str,
        repo=DistGit,
    ).and_return(flexmock())
    api_mock.sync_release(version="1.1", dist_git_branch="_", add_pr_instructions=True)


@pytest.mark.parametrize(
    "resolved_bugs, result",
    [
        pytest.param(
            ["rhbz#123"],
            "- Resolves rhbz#123\nUpstream tag: 1.0.0\nUpstream commit: _\n",
        ),
        pytest.param(
            ["rhbz#123", "rhbz#222"],
            "- Resolves rhbz#123\n- Resolves rhbz#222\nUpstream tag: 1.0.0\nUpstream commit: _\n",
        ),
        pytest.param(None, "Upstream tag: 1.0.0\nUpstream commit: _\n"),
    ],
)
def test_get_default_commit_description(api_mock, resolved_bugs, result):
    assert (
        api_mock.get_default_commit_description("1.0.0", resolved_bugs=resolved_bugs)
        == result
    )


@pytest.mark.parametrize(
    "package_config, config, expected_pkg_tool",
    (
        pytest.param(
            flexmock(pkg_tool=None),
            Config(),
            "fedpkg",
            id="default from config",
        ),
        pytest.param(
            flexmock(pkg_tool="rhpkg"),
            Config(),
            "rhpkg",
            id="package-level override",
        ),
        # regression in automated allowlisting
        pytest.param(None, Config(), "fedpkg", id="no package_config given"),
    ),
)
def test_pkg_tool_property(package_config, config, expected_pkg_tool):
    assert PackitAPI(config, package_config).pkg_tool == expected_pkg_tool
