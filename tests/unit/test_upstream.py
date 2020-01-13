import pytest

from flexmock import flexmock
from packit.actions import ActionName
from packit.local_project import LocalProject
from packit.upstream import Upstream
from tests.spellbook import get_test_config


@pytest.fixture
def package_config_mock():
    mock = flexmock(synced_files=None)
    return mock


@pytest.fixture
def git_project_mock():
    mock = flexmock(upstream_project_url="dummy_url")
    return mock


@pytest.fixture
def local_project_mock(git_project_mock):
    mock = flexmock(git_project=git_project_mock)
    return mock


@pytest.fixture
def upstream_mock(local_project_mock, package_config_mock):
    upstream = Upstream(
        config=get_test_config(),
        package_config=package_config_mock,
        local_project=LocalProject(working_dir=str("test")),
    )
    flexmock(upstream)
    upstream.should_receive("local_project").and_return(local_project_mock)
    return upstream


@pytest.fixture
def upstream_pr_mock():
    mock = flexmock(url="test_pr_url")
    return mock


@pytest.mark.parametrize(
    "fork_username",
    [
        pytest.param("test_fork_username", id="fork_username_set"),
        pytest.param(None, id="fork_username_None"),
    ],
)
def test_create_pull(upstream_mock, upstream_pr_mock, fork_username):
    upstream_mock.local_project.git_project.should_receive("pr_create").with_args(
        title="test_title",
        body="test_description",
        source_branch="test_source",
        target_branch="test_target",
        fork_username=fork_username,
    ).and_return(upstream_pr_mock)
    upstream_mock.create_pull(
        pr_title="test_title",
        pr_description="test_description",
        source_branch="test_source",
        target_branch="test_target",
        fork_username=fork_username,
    )


@pytest.mark.parametrize(
    "action_config,result",
    [
        pytest.param("one cmd", [["one", "cmd"]], id="str_command"),
        pytest.param(["one cmd"], [["one", "cmd"]], id="list_command"),
        pytest.param([["one", "cmd"]], [["one", "cmd"]], id="list_in_list_command"),
        pytest.param(
            ["one cmd", "second cmd"],
            [["one", "cmd"], ["second", "cmd"]],
            id="two_str_commands_in_list",
        ),
        pytest.param(
            [["one", "cmd"], ["second", "cmd"]],
            [["one", "cmd"], ["second", "cmd"]],
            id="two_list_commands_in_list",
        ),
        pytest.param(
            [["one", "cmd"], "second cmd"],
            [["one", "cmd"], ["second", "cmd"]],
            id="one_str_and_one_list_command_in_list",
        ),
    ],
)
def test_get_commands_for_actions(action_config, result):
    ups = Upstream(
        package_config=flexmock(
            actions={ActionName.create_archive: action_config}, synced_files=flexmock()
        ),
        config=flexmock(),
        local_project=flexmock(),
    )
    assert ups.get_commands_for_actions(action=ActionName.create_archive) == result
