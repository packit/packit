# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Optional, Union

from flexmock import flexmock

from packit.local_project import LocalProject
from packit.utils import commands
from tests.integration.conftest import DOWNSTREAM_PROJECT_URL


def test_basic_build(
    cwd_upstream_or_distgit,
    api_instance,
    mock_remote_functionality_upstream,
):
    u, d, api = api_instance
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()

    def run_command_remote(
        cmd,
        error_message=None,
        cwd=None,
        fail=True,
        output=False,
        env=None,
        print_live=False,
    ):
        assert cmd[:-1] == ["koji", "build", "--scratch", "--nowait", "asdqwe"]
        assert cmd[-1].startswith(f"git+{DOWNSTREAM_PROJECT_URL}")
        assert cwd == api.dg.local_project.working_dir
        assert fail
        assert output
        assert print_live
        return flexmock(stdout="")

    flexmock(commands).should_receive("run_command_remote").replace_with(
        run_command_remote,
    ).once()

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
