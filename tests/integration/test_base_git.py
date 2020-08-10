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

import pytest
from git import PushInfo

from flexmock import flexmock
from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.exceptions import PackitException
from packit.config import Config, PackageConfig, RunCommandType
from packit.local_project import LocalProject
from tests.spellbook import can_a_module_be_imported


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
    packit_repository_base.local_project = LocalProject(working_dir="/tmp")

    flexmock(Sandcastle).should_receive("run")
    flexmock(Sandcastle).should_receive("exec").and_return(echo_cmd)
    flexmock(Sandcastle).should_receive("delete_pod").and_return(None)
    result = packit_repository_base.get_output_from_action(ActionName.pre_sync)
    assert result[-1] == echo_cmd


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


def test_base_push_bad(distgit_and_remote):
    distgit, _ = distgit_and_remote

    b = PackitRepositoryBase(config=Config(), package_config=PackageConfig())
    b.local_project = LocalProject(
        working_dir=distgit, git_url="https://github.com/packit/lol"
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
        working_dir=distgit, git_url="https://github.com/packit/lol"
    )
    flexmock(
        LocalProject,
        push=lambda *args, **kwargs: [
            PushInfo(PushInfo.FAST_FORWARD, None, None, None, None)
        ],
    )
    b.push("master")
