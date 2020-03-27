import pytest

from flexmock import flexmock
from packit.actions import ActionName
from packit.local_project import LocalProject
from packit.upstream import Upstream
from tests.spellbook import get_test_config
from packit.command_handler import LocalCommandHandler
import packit.upstream as upstream_module
import datetime


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


def test__get_last_tag(upstream_mock):
    flexmock(upstream_module)\
        .should_receive("run_command")\
        .once()\
        .with_args(["git", "describe", "--tags", "--abbrev=0"], output=True)\
        .and_return("1.5")
    last_tag = upstream_mock._get_last_tag()
    assert last_tag == "1.5"


def test_fix_spec_changelog_message_should_be_actual_commits():
    flexmock(upstream_module).should_receive("run_command")\
        .times(2)\
        .and_return("v1.5.0-14-g241472")\
        .and_return("actual commit")
    version = "random-version"
    commit = "61fad52477f511eab9ba"
    specfile = flexmock()
    specfile.should_receive("get_release_number").and_return("1.5.aerd")
    specfile.should_receive("set_spec_version")
    upstream = Upstream(
        package_config=flexmock(
            actions={ActionName.fix_spec: flexmock()}, synced_files=flexmock()
        ),
        config=flexmock(),
        local_project=flexmock(),
    )
    flexmock(upstream)
    upstream.should_receive("_fix_spec_source").with_args("archive")
    upstream.should_receive("_fix_spec_prep").with_args(version)
    upstream.should_receive("_get_last_tag").and_return("1.5")
    upstream.should_receive("specfile").and_return(specfile)
    upstream.fix_spec("archive", version, commit)
