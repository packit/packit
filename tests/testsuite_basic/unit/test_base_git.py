import pytest
from flexmock import flexmock
from git import PushInfo

from packit import utils
from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.command_handler import LocalCommandHandler, SandcastleCommandHandler
from packit.config import PackageConfig, Config, RunCommandType
from packit.distgit import DistGit
from packit.exceptions import PackitException
from packit.local_project import LocalProject
from packit.upstream import Upstream
from tests.testsuite_basic.spellbook import can_a_module_be_imported


@pytest.fixture()
def distgit_with_actions():
    return DistGit(
        config=flexmock(Config()),
        package_config=flexmock(
            PackageConfig(
                downstream_package_name="beer",
                actions={
                    ActionName.pre_sync: "command --a",
                    ActionName.get_current_version: "command --b",
                },
            )
        ),
    )


@pytest.fixture()
def upstream_with_actions():
    return Upstream(
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
def packit_repository_base():
    return PackitRepositoryBase(
        config=Config(),
        package_config=PackageConfig(
            actions={
                ActionName.pre_sync: "command --a",
                ActionName.get_current_version: "command --b",
            }
        ),
    )


@pytest.fixture()
def packit_repository_base_more_actions():
    return PackitRepositoryBase(
        config=Config(),
        package_config=PackageConfig(
            actions={
                ActionName.pre_sync: ["command --a", "command --a"],
                ActionName.get_current_version: "command --b",
            }
        ),
    )


@pytest.fixture()
def packit_repository_base_with_sandcastle_object():
    c = Config()
    c.command_handler = RunCommandType.sandcastle
    b = PackitRepositoryBase(
        config=c,
        package_config=PackageConfig(
            actions={
                ActionName.pre_sync: "command -a",
                ActionName.get_current_version: "command -b",
            }
        ),
    )
    b.local_project = LocalProject()
    return b


def test_has_action_upstream(upstream_with_actions):
    assert upstream_with_actions.has_action(ActionName.pre_sync)
    assert not upstream_with_actions.has_action(ActionName.create_patches)


def test_has_action_distgit(distgit_with_actions):
    assert distgit_with_actions.has_action(ActionName.pre_sync)
    assert not distgit_with_actions.has_action(ActionName.create_patches)


def test_with_action_non_defined(packit_repository_base):
    if packit_repository_base.with_action(action=ActionName.create_patches):
        # this is the style we are using that function
        return

    assert False


def test_with_action_defined(packit_repository_base):
    flexmock(utils).should_receive("run_command").once()

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    if packit_repository_base.with_action(action=ActionName.pre_sync):
        # this is the style we are using that function
        assert False


def test_with_action_working_dir(packit_repository_base):
    flexmock(LocalCommandHandler).should_receive("run_command").with_args(
        command=["command", "--a"], env=None
    ).and_return("command --a").once()

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    assert not packit_repository_base.with_action(action=ActionName.pre_sync)


def test_run_action_hook_not_defined(packit_repository_base):
    flexmock(utils).should_receive("run_command").times(0)

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    packit_repository_base.run_action(actions=ActionName.create_patches)


def test_run_action_not_defined(packit_repository_base):
    flexmock(LocalCommandHandler).should_receive("run_command").times(0)

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
        ActionName.create_patches, action_method, "arg", kwarg="kwarg"
    )


def test_run_action_defined(packit_repository_base):
    flexmock(LocalCommandHandler).should_receive("run_command").with_args(
        command=["command", "--a"], env=None
    ).and_return("command --a").once()

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    action_method = (
        flexmock()
        .should_receive("action_function")
        .with_args("arg", kwarg="kwarg")
        .times(0)
        .mock()
        .action_function
    )

    packit_repository_base.run_action(
        ActionName.pre_sync, action_method, "arg", "kwarg"
    )


@pytest.mark.skipif(
    not can_a_module_be_imported("sandcastle"), reason="sandcastle is not installed"
)
def test_run_action_in_sandcastle(packit_repository_base_with_sandcastle_object):
    from sandcastle import Sandcastle

    flexmock(Sandcastle).should_receive("get_api_client").and_return(None)
    flexmock(SandcastleCommandHandler).should_receive("run_command").with_args(
        command=["command", "-a"], env=None
    ).and_return(None).once()
    packit_repository_base_with_sandcastle_object.config.actions_handler = "sandcastle"
    packit_repository_base_with_sandcastle_object.run_action(
        ActionName.pre_sync, None, "arg", "kwarg"
    )


def test_run_action_more_actions(packit_repository_base_more_actions):
    flexmock(LocalCommandHandler).should_receive("run_command").times(2)

    packit_repository_base_more_actions.local_project = flexmock(
        working_dir="my/working/dir"
    )

    action_method = (
        flexmock()
        .should_receive("action_function")
        .with_args("arg", kwarg="kwarg")
        .times(0)
        .mock()
        .action_function
    )
    packit_repository_base_more_actions.run_action(
        ActionName.pre_sync, action_method, "arg", kwarg="kwarg"
    )


def test_get_output_from_action_not_defined(packit_repository_base):
    flexmock(LocalCommandHandler).should_receive("run_command").times(0)

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    result = packit_repository_base.get_output_from_action(ActionName.create_patches)
    assert result is None


def test_base_push_bad(distgit_and_remote):
    distgit, _ = distgit_and_remote

    b = PackitRepositoryBase(config=Config(), package_config=PackageConfig())
    b.local_project = LocalProject(
        working_dir=str(distgit), git_url="https://github.com/packit-service/lol"
    )
    flexmock(
        LocalProject,
        push=lambda *args, **kwargs: [
            PushInfo(PushInfo.REMOTE_REJECTED, None, None, None, None)
        ],
    )
    with pytest.raises(PackitException) as e:
        b.push("master")
    assert "unable to push" in str(e.value)


def test_base_push_good(distgit_and_remote):
    distgit, _ = distgit_and_remote

    b = PackitRepositoryBase(config=Config(), package_config=PackageConfig())
    b.local_project = LocalProject(
        working_dir=str(distgit), git_url="https://github.com/packit-service/lol"
    )
    flexmock(
        LocalProject,
        push=lambda *args, **kwargs: [
            PushInfo(PushInfo.FAST_FORWARD, None, None, None, None)
        ],
    )
    b.push("master")
