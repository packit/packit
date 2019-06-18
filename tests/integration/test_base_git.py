import pytest
from flexmock import flexmock

from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.config import PackageConfig, Config, RunCommandType

from sandcastle.api import Sandcastle

from packit.local_project import LocalProject


def test_get_output_from_action_defined():
    echo_cmd = "echo 'hello world'"

    packit_repository_base = PackitRepositoryBase(
        config=flexmock(Config()),
        package_config=flexmock(PackageConfig(actions={ActionName.pre_sync: echo_cmd})),
    )

    packit_repository_base.local_project = flexmock(working_dir=".")

    result = packit_repository_base.get_output_from_action(ActionName.pre_sync)
    assert result == "hello world\n"


def test_get_output_from_action_defined_in_sandcastle():
    echo_cmd = "hello world"
    flexmock(Sandcastle).should_receive("get_api_client")
    flexmock(Sandcastle).should_receive("is_pod_already_deployed").and_return(True)
    c = Config()
    c.command_handler = RunCommandType.sandcastle
    packit_repository_base = PackitRepositoryBase(
        config=c, package_config=PackageConfig(actions={ActionName.pre_sync: echo_cmd})
    )
    packit_repository_base.local_project = LocalProject()

    flexmock(Sandcastle).should_receive("run")
    flexmock(Sandcastle).should_receive("exec").and_return(echo_cmd)
    result = packit_repository_base.get_output_from_action(ActionName.pre_sync)
    assert result == echo_cmd


@pytest.mark.skip(
    reason="Skipping since we don't have an OpenShift cluster by default."
)
def test_run_in_sandbox():
    packit_repository_base = PackitRepositoryBase(
        config=Config(),
        package_config=PackageConfig(actions={ActionName.pre_sync: "ls -lha"}),
    )
    packit_repository_base.config.actions_handler = "sandcastle"

    result = packit_repository_base.get_output_from_action(ActionName.pre_sync)
    assert "total 4.0K" in result
    assert "drwxr-xr-x. 1 root root" in result
