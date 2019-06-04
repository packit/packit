import pytest
from flexmock import flexmock

from packit import utils
from packit.actions import ActionName
from packit.command_runner import CommandRunner
from packit.config import PackageConfig, Config


@pytest.fixture()
def command_runner_with_actions():
    return CommandRunner(
        config=flexmock(Config()),
        package_config=flexmock(
            PackageConfig(
                actions={
                    ActionName.pre_sync: "command --a",
                    ActionName.get_current_version: "command --b",
                }
            )
        ),
        local_project=flexmock(
            repo_name=flexmock(),
            refresh_the_arguments=lambda: None,
            git_project=flexmock(),
            git_service=flexmock(),
        ),
    )


@pytest.fixture()
def command_runner():
    return CommandRunner(
        config=flexmock(),
        package_config=flexmock(
            PackageConfig(
                actions={
                    ActionName.pre_sync: "command --a",
                    ActionName.get_current_version: "command --b",
                }
            )
        ),
    )


def test_has_action(command_runner_with_actions):
    assert command_runner_with_actions.has_action(ActionName.pre_sync)
    assert not command_runner_with_actions.has_action(ActionName.create_patches)


def test_with_action_non_defined(command_runner):
    if command_runner.with_action(action=ActionName.create_patches):
        # this is the style we are using that function
        return

    assert False


def test_with_action_defined(command_runner):
    flexmock(utils).should_receive("run_command").once()

    command_runner.local_project = flexmock(working_dir="my/working/dir")

    if command_runner.with_action(action=ActionName.pre_sync):
        # this is the style we are using that function
        assert False


def test_with_action_working_dir(command_runner):
    flexmock(utils).should_receive("run_command").with_args(
        cmd="command --a", cwd="my/working/dir"
    ).once()

    command_runner.local_project = flexmock(working_dir="my/working/dir")

    assert not command_runner.with_action(action=ActionName.pre_sync)


def test_run_action_hook_not_defined(command_runner):
    flexmock(utils).should_receive("run_command").times(0)

    command_runner.local_project = flexmock(working_dir="my/working/dir")

    command_runner.run_action(action=ActionName.create_patches)


def test_run_action_not_defined(command_runner):
    flexmock(utils).should_receive("run_command").times(0)

    command_runner.local_project = flexmock(working_dir="my/working/dir")

    action_method = (
        flexmock()
        .should_receive("action_function")
        .with_args("arg", kwarg="kwarg")
        .once()
        .mock()
        .action_function
    )

    command_runner.run_action(
        ActionName.create_patches, action_method, "arg", kwarg="kwarg"
    )


def test_run_action_defined(command_runner):
    flexmock(utils).should_receive("run_command").with_args(
        cmd="command --a", cwd="my/working/dir"
    ).once()

    command_runner.local_project = flexmock(working_dir="my/working/dir")

    action_method = (
        flexmock()
        .should_receive("action_function")
        .with_args("arg", kwarg="kwarg")
        .times(0)
        .mock()
        .action_function
    )

    command_runner.run_action(ActionName.pre_sync, action_method, "arg", kwarg="kwarg")


def test_get_output_from_action_not_defined(command_runner):
    flexmock(utils).should_receive("run_command").times(0)

    command_runner.local_project = flexmock(working_dir="my/working/dir")

    result = command_runner.get_output_from_action(ActionName.create_patches)
    assert result is None
