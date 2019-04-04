import pytest
from flexmock import flexmock

from packit import utils
from packit.config import PackageConfig, Config
from packit.distgit import DistGit


@pytest.fixture()
def distgit_with_actions():
    return DistGit(
        config=flexmock(Config()),
        package_config=flexmock(
            PackageConfig(
                actions={"action-a": "command --a", "action-b": "command --b"}
            )
        ),
    )


@pytest.fixture()
def upstream_with_actions():
    return DistGit(
        config=flexmock(Config()),
        package_config=flexmock(
            PackageConfig(
                actions={"action-a": "command --a", "action-b": "command --b"}
            )
        ),
    )


def test_has_action_upstream(upstream_with_actions):
    assert upstream_with_actions.has_action("action-a")
    assert not upstream_with_actions.has_action("action-c")


def test_has_action_distgit(distgit_with_actions):
    assert distgit_with_actions.has_action("action-a")
    assert not distgit_with_actions.has_action("action-c")


@pytest.mark.parametrize(
    "base_git_fixture", [distgit_with_actions, upstream_with_actions]
)
def test_with_action_non_defined(base_git_fixture):
    base_git = base_git_fixture()

    if base_git.with_action(action_name="unknown-action"):
        # this is the style we are using that function
        return

    assert False


@pytest.mark.parametrize(
    "base_git_fixture", [distgit_with_actions, upstream_with_actions]
)
def test_with_action_defined(base_git_fixture):
    flexmock(utils).should_receive("run_command").once()

    base_git = base_git_fixture()
    base_git._local_project = flexmock(working_dir="my/working/dir")

    if base_git.with_action(action_name="action-a"):
        # this is the style we are using that function
        assert False


@pytest.mark.parametrize(
    "base_git_fixture", [distgit_with_actions, upstream_with_actions]
)
def test_with_action_working_dir(base_git_fixture):
    flexmock(utils).should_receive("run_command").with_args(
        cmd="command --a", cwd="my/working/dir"
    ).once()

    base_git = base_git_fixture()
    base_git._local_project = flexmock(working_dir="my/working/dir")

    assert not base_git.with_action(action_name="action-a")


@pytest.mark.parametrize(
    "base_git_fixture", [distgit_with_actions, upstream_with_actions]
)
def test_run_action_hook_not_defined(base_git_fixture):
    flexmock(utils).should_receive("run_command").times(0)

    base_git = base_git_fixture()
    base_git._local_project = flexmock(working_dir="my/working/dir")

    base_git.run_action(action_name="not-defined")


@pytest.mark.parametrize(
    "base_git_fixture", [distgit_with_actions, upstream_with_actions]
)
def test_run_action_not_defined(base_git_fixture):
    flexmock(utils).should_receive("run_command").times(0)

    base_git = base_git_fixture()
    base_git._local_project = flexmock(working_dir="my/working/dir")

    action_method = (
        flexmock()
        .should_receive("action_function")
        .with_args("arg", kwarg="kwarg")
        .once()
        .mock()
        .action_function
    )

    base_git.run_action("not-defined", action_method, "arg", kwarg="kwarg")


@pytest.mark.parametrize(
    "base_git_fixture", [distgit_with_actions, upstream_with_actions]
)
def test_run_action_defined(base_git_fixture):
    flexmock(utils).should_receive("run_command").with_args(
        cmd="command --a", cwd="my/working/dir"
    ).once()

    base_git = base_git_fixture()
    base_git._local_project = flexmock(working_dir="my/working/dir")

    action_method = (
        flexmock()
        .should_receive("action_function")
        .with_args("arg", kwarg="kwarg")
        .times(0)
        .mock()
        .action_function
    )

    base_git.run_action("action-a", action_method, "arg", kwarg="kwarg")


@pytest.mark.parametrize(
    "base_git_fixture", [distgit_with_actions, upstream_with_actions]
)
def test_get_output_from_action_not_defined(base_git_fixture):
    flexmock(utils).should_receive("run_command").times(0)

    base_git = base_git_fixture()
    base_git._local_project = flexmock(working_dir="my/working/dir")

    result = base_git.get_output_from_action("not-defined")
    assert result is None
