# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import logging
from pathlib import Path
from typing import List, Optional, Dict, Union

import pytest
from flexmock import flexmock
from rebasehelper.helpers.download_helper import DownloadHelper

from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.command_handler import LocalCommandHandler
from packit.config import Config, RunCommandType, PackageConfig
from packit.config.sources import SourcesItem
from packit.distgit import DistGit
from packit.local_project import LocalProject
from packit.specfile import Specfile
from packit.upstream import Upstream
from packit.utils import commands
from tests.spellbook import can_a_module_be_imported


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
def packit_repository_base_with_sandcastle_object(tmp_path):
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
    b.local_project = LocalProject(working_dir=tmp_path)
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
    flexmock(commands).should_receive("run_command").once()

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    if packit_repository_base.with_action(action=ActionName.pre_sync):
        # this is the style we are using that function
        assert False


def test_with_action_working_dir(packit_repository_base):
    flexmock(LocalCommandHandler).should_receive("run_command").with_args(
        command=["command", "--a"], env=None, print_live=True
    ).and_return("command --a").once()

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    assert not packit_repository_base.with_action(action=ActionName.pre_sync)


def test_run_action_hook_not_defined(packit_repository_base):
    flexmock(commands).should_receive("run_command").times(0)

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
        command=["command", "--a"], env=None, print_live=True
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
def test_run_action_in_sandcastle(
    packit_repository_base_with_sandcastle_object, caplog
):
    from sandcastle import Sandcastle

    flexmock(Sandcastle).should_receive("get_api_client").and_return(None).once()
    flexmock(Sandcastle).should_receive("run").and_return(None).once()

    def mocked_exec(
        command: List[str],
        env: Optional[Dict] = None,
        cwd: Union[str, Path] = None,
    ):
        if command == ["command", "-b"]:
            return "1.2.3"
        elif command == ["command", "-a"]:
            return (
                "make po-pull\n"
                "make[1]: Entering directory "
                "'/sandcastle/docker-io-usercont-sandcastle-prod-20200820-160948197515'\n"
                "TEMP_DIR=$(mktemp --tmpdir -d anaconda-localization-XXXXXXXXXX)\n"
            )
        else:
            raise Exception("This command was not expected")

    flexmock(Sandcastle, exec=mocked_exec)
    flexmock(Sandcastle).should_receive("delete_pod").once().and_return(None)
    with caplog.at_level(logging.INFO, logger="packit"):
        packit_repository_base_with_sandcastle_object.run_action(
            ActionName.pre_sync, None, "arg1", "kwarg1"
        )
        packit_repository_base_with_sandcastle_object.run_action(
            ActionName.get_current_version, None, "arg2", "kwarg2"
        )
        # this is being called in PackitAPI.clean
        packit_repository_base_with_sandcastle_object.command_handler.clean()
        # leading space means that we have the output actually printed
        # and it's not a single line with the whole output
        assert " Running command: command -a\n" in caplog.text
        assert " make po-pull\n" in caplog.text
        assert " anaconda-localization-XXXXXXXXXX)\n" in caplog.text
        assert " 1.2.3\n" in caplog.text


@pytest.mark.skipif(
    not can_a_module_be_imported("sandcastle"), reason="sandcastle is not installed"
)
def test_command_handler_is_set(packit_repository_base_with_sandcastle_object):
    from sandcastle import Sandcastle

    flexmock(Sandcastle).should_receive("get_api_client").and_return(None).once()
    flexmock(Sandcastle).should_receive("run").and_return(None).once()

    # it's not set initially
    assert not packit_repository_base_with_sandcastle_object.is_command_handler_set()

    # and should be set once we invoke it
    assert packit_repository_base_with_sandcastle_object.command_handler.sandcastle
    assert packit_repository_base_with_sandcastle_object.is_command_handler_set()


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


@pytest.mark.parametrize(
    "source, package_config, expected_url",
    [
        pytest.param(
            "https://download.samba.org/pub/rsync/src/rsync-3.1.3.tar.gz",
            PackageConfig(
                specfile_path="rsync.spec",
                sources=[
                    SourcesItem(
                        path="rsync-3.1.3.tar.gz",
                        url="https://git.centos.org/sources/rsync/c8s/82e7829",
                    ),
                ],
                jobs=[],
            ),
            "https://git.centos.org/sources/rsync/c8s/82e7829",
        ),
        pytest.param(
            "https://download.samba.org/pub/rsync/src/rsync-3.1.3.tar.gz",
            PackageConfig(
                specfile_path="rsync.spec",
                sources=[
                    SourcesItem(
                        path="rsync-3.1.3.tar.gz",
                        url="https://git.centos.org/sources/rsync/c8s/82e7829",
                    ),
                ],
                jobs=[],
            ),
            "https://git.centos.org/sources/rsync/c8s/82e7829",
        ),
        pytest.param(
            "rsync-3.1.3.tar.gz",
            PackageConfig(
                specfile_path="rsync.spec",
                sources=[
                    SourcesItem(
                        path="rsync-3.1.3.tar.gz",
                        url="https://git.centos.org/sources/rsync/c8s/82e7829",
                    ),
                ],
                jobs=[],
            ),
            "https://git.centos.org/sources/rsync/c8s/82e7829",
        ),
    ],
)
def test_download_remote_sources(source, package_config, expected_url, tmp_path: Path):
    specfile_content = (
        "Name: rsync\n"
        "Version: 3.1.3\n"
        "Release: 1\n"
        f"Source0: {source}\n"
        "License: GPLv3+\n"
        "Summary: rsync\n"
        "%description\nrsync\n"
    )
    spec_path = tmp_path / "rsync.spec"
    spec_path.write_text(specfile_content)
    specfile = Specfile(spec_path, sources_dir=tmp_path)
    base_git = PackitRepositoryBase(config=flexmock(), package_config=package_config)
    flexmock(base_git).should_receive("specfile").and_return(specfile)

    expected_path = tmp_path / "rsync-3.1.3.tar.gz"

    # sadly we can't mock os.path.is_file, b/c the function is defined in posixpath.py
    # and flexmock is not able to mock that
    def mocked_download_file(url, destination_path, blocksize=8192):
        assert url == expected_url
        Path(destination_path).write_text("1")

    flexmock(DownloadHelper, download_file=mocked_download_file)

    base_git.download_remote_sources()

    flexmock(DownloadHelper).should_receive("download_file").and_raise(
        Exception(
            "This should not be called second time since the source is present already."
        )
    )
    base_git.download_remote_sources()

    assert expected_path.exists()
