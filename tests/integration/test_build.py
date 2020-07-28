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

from pathlib import Path
from typing import Union, List, Optional, Dict

from flexmock import flexmock

from packit.utils import commands


def test_basic_build(
    cwd_upstream_or_distgit, api_instance, mock_remote_functionality_upstream
):
    u, d, api = api_instance
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    flexmock(commands).should_receive("run_command_remote").with_args(
        cmd=["fedpkg", "build", "--scratch", "--nowait", "--target", "asdqwe"],
        cwd=api.dg.local_project.working_dir,
        error_message="Submission of build to koji failed.",
        fail=True,
    ).once()

    api.build("master", scratch=True, nowait=True, koji_target="asdqwe")


def test_build_from_upstream(
    cwd_upstream_or_distgit, api_instance, mock_remote_functionality_upstream
):
    u, d, api = api_instance

    def mocked_run_command(
        cmd: Union[List[str], str],
        error_message: str = None,
        cwd: Union[str, Path] = None,
        fail: bool = True,
        output: bool = False,
        env: Optional[Dict] = None,
        decode=True,
        print_live=False,
    ):
        assert cmd[:-1] == ["koji", "build", "--scratch", "--nowait", "hadron-collider"]
        srpm_path = cmd[-1]
        assert Path(srpm_path).is_file()
        assert srpm_path.endswith(".src.rpm")
        assert cwd == api.up.local_project.working_dir
        return "\n\nLink to koji build: https://koji...\n"

    flexmock(commands, run_command_remote=mocked_run_command)
    api.build(
        "master",
        scratch=True,
        nowait=True,
        from_upstream=True,
        koji_target="hadron-collider",
    )
