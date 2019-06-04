from flexmock import flexmock

from packit.actions import ActionName
from packit.config import PackageConfig
from packit.command_runner import CommandRunner


def test_get_output_from_action_defined():
    echo_cmd = "echo 'hello world'"

    command_runner = CommandRunner(
        config=flexmock(),
        package_config=flexmock(PackageConfig(actions={ActionName.pre_sync: echo_cmd})),
        local_project=flexmock(working_dir="."),
    )

    result = command_runner.get_output_from_action(ActionName.pre_sync)
    assert result == "hello world\n"
