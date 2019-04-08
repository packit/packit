from flexmock import flexmock

from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.config import PackageConfig


def test_get_output_from_action_defined():
    echo_cmd = "echo 'hello world'"

    packit_repository_base = PackitRepositoryBase(
        config=flexmock(),
        package_config=flexmock(PackageConfig(actions={ActionName.pre_sync: echo_cmd})),
    )

    packit_repository_base.local_project = flexmock(working_dir=".")

    result = packit_repository_base.get_output_from_action(ActionName.pre_sync)
    assert result == "hello world\n"
