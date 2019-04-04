import pytest
from flexmock import flexmock

from tests.unit.test_base_git import distgit_with_actions, upstream_with_actions


@pytest.mark.parametrize(
    "base_git_fixture", [distgit_with_actions, upstream_with_actions]
)
def test_get_output_from_action_defined(base_git_fixture):
    echo_cmd = "echo 'hello world'"

    base_git = base_git_fixture()
    base_git._local_project = flexmock(working_dir=".")
    base_git.package_config.actions = {"action-a": echo_cmd}

    result = base_git.get_output_from_action("action-a")
    assert result == "hello world\n"
