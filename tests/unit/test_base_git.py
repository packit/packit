import pytest
from flexmock import flexmock

from packit import utils
from packit.base_git import PackitRepositoryBase
from packit.config import PackageConfig, Config
from packit.distgit import DistGit
from packit.upstream import Upstream


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
    return Upstream(
        config=flexmock(Config()),
        package_config=flexmock(
            PackageConfig(
                actions={"action-a": "command --a", "action-b": "command --b"}
            )
        ),
        local_project=flexmock(repo_name=flexmock()),
    )


@pytest.fixture()
def packit_repository_base():
    return PackitRepositoryBase(
        config=flexmock(),
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


def test_with_action_non_defined(packit_repository_base):
    if packit_repository_base.with_action(action_name="unknown-action"):
        # this is the style we are using that function
        return

    assert False


def test_with_action_defined(packit_repository_base):
    flexmock(utils).should_receive("run_command").once()

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    if packit_repository_base.with_action(action_name="action-a"):
        # this is the style we are using that function
        assert False


def test_with_action_working_dir(packit_repository_base):
    flexmock(utils).should_receive("run_command").with_args(
        cmd="command --a", cwd="my/working/dir"
    ).once()

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    assert not packit_repository_base.with_action(action_name="action-a")


def test_run_action_hook_not_defined(packit_repository_base):
    flexmock(utils).should_receive("run_command").times(0)

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    packit_repository_base.run_action(action_name="not-defined")


def test_run_action_not_defined(packit_repository_base):
    flexmock(utils).should_receive("run_command").times(0)

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    action_method = (
        flexmock()
        .should_receive("action_function")
        .with_args("arg", kwarg="kwarg")
        .once()
        .mock()
        .action_function
    )

    packit_repository_base.run_action(
        "not-defined", action_method, "arg", kwarg="kwarg"
    )


def test_run_action_defined(packit_repository_base):
    flexmock(utils).should_receive("run_command").with_args(
        cmd="command --a", cwd="my/working/dir"
    ).once()

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    action_method = (
        flexmock()
        .should_receive("action_function")
        .with_args("arg", kwarg="kwarg")
        .times(0)
        .mock()
        .action_function
    )

    packit_repository_base.run_action("action-a", action_method, "arg", kwarg="kwarg")


def test_get_output_from_action_not_defined(packit_repository_base):
    flexmock(utils).should_receive("run_command").times(0)

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    result = packit_repository_base.get_output_from_action("not-defined")
    assert result is None
