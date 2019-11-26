import pytest

from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.config import Config, PackageConfig


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
