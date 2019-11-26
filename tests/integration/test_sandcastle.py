import pytest

from flexmock import flexmock
from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.config import Config, PackageConfig, RunCommandType
from packit.local_project import LocalProject
from tests.spellbook import can_a_module_be_imported


@pytest.mark.skipif(
    not can_a_module_be_imported("sandcastle"), reason="sandcastle is not installed"
)
def test_get_output_from_action_defined_in_sandcastle():
    from sandcastle.api import Sandcastle

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
    flexmock(Sandcastle).should_receive("delete_pod").and_return(None)
    result = packit_repository_base.get_output_from_action(ActionName.pre_sync)
    assert result[-1] == echo_cmd
