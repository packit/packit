# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Optional, Union

from flexmock import flexmock

from packit.local_project import LocalProject
from packit.utils import commands


def test_basic_build(
    cwd_upstream_or_distgit,
    api_instance,
    mock_remote_functionality_upstream,
):
    u, d, api = api_instance
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()
    flexmock(commands).should_receive("run_command_remote").with_args(
        cmd=["fedpkg", "build", "--scratch", "--nowait", "--target", "asdqwe"],
        cwd=api.dg.local_project.working_dir,
        error_message="Submission of build to koji failed.",
        fail=True,
        output=True,
        print_live=True,
    ).once().and_return(flexmock(stdout=""))

    api.build("main", scratch=True, nowait=True, koji_target="asdqwe")


def test_build_from_upstream(
    cwd_upstream_or_distgit,
    api_instance,
    mock_remote_functionality_upstream,
):
    u, d, api = api_instance

    def mocked_run_command(
        cmd: Union[list[str], str],
        error_message: Optional[str] = None,
        cwd: Optional[Union[str, Path]] = None,
        fail: bool = True,
        output: bool = False,
        env: Optional[dict] = None,
        decode=True,
        print_live=False,
    ):
        assert cmd[:-1] == ["koji", "build", "--scratch", "--nowait", "hadron-collider"]
        srpm_path = cmd[-1]
        assert Path(srpm_path).is_file()
        assert srpm_path.endswith(".src.rpm")
        assert cwd == api.up.local_project.working_dir
        return flexmock(
            success=True,
            stdout="\n\nLink to koji build: https://koji...\n",
        )

    flexmock(commands, run_command_remote=mocked_run_command)
    flexmock(LocalProject).should_receive("free_resources")
    api.build(
        "master",
        scratch=True,
        nowait=True,
        from_upstream=True,
        koji_target="hadron-collider",
    )
