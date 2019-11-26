import pytest

from flexmock import flexmock
from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.config import Config, PackageConfig
from packit.exceptions import PackitException


@pytest.mark.parametrize(
    "echo_cmd, expected_output",
    [
        ("echo 'hello world'", ["hello world\n"]),
        # should return output of only the last one
        (["echo 'ignore me'", "echo 'hello world'"], ["ignore me\n", "hello world\n"]),
    ],
)
def test_get_output_from_action_defined(echo_cmd, expected_output):
    packit_repository_base = PackitRepositoryBase(
        config=flexmock(Config()),
        package_config=flexmock(PackageConfig(actions={ActionName.pre_sync: echo_cmd})),
    )

    packit_repository_base.local_project = flexmock(working_dir=".")

    result = packit_repository_base.get_output_from_action(ActionName.pre_sync)
    assert result == expected_output


def test_distgit_commit_empty(distgit_instance):
    d, dg = distgit_instance
    with pytest.raises(PackitException) as ex:
        dg.commit("", "")
    assert (
        str(ex.value)
        == "No changes are present in the dist-git repo: nothing to commit."
    )
