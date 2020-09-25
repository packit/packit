# MIT License
#
# Copyright (c) 2020 Red Hat, Inc.

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

"""
Functional tests for local-build command
"""
from pathlib import Path
from subprocess import CalledProcessError

import pytest

from tests.functional.spellbook import call_real_packit


def test_rpm_command(ogr_distgit_and_remote):
    call_real_packit(
        parameters=["--debug", "local-build"], cwd=ogr_distgit_and_remote[0]
    )
    rpm_paths = ogr_distgit_and_remote[0].glob("noarch/*.rpm")

    assert all([rpm_path.exists() for rpm_path in rpm_paths])


def test_local_build_with_remote_good(ogr_distgit_and_remote):
    call_real_packit(
        parameters=["--debug", "--remote", "origin", "local-build"],
        cwd=ogr_distgit_and_remote[0],
    )
    rpm_paths = ogr_distgit_and_remote[0].glob("noarch/*.rpm")

    assert all([rpm_path.exists() for rpm_path in rpm_paths])


def test_local_build_with_remote_bad(ogr_distgit_and_remote):
    with pytest.raises(CalledProcessError) as ex:
        call_real_packit(
            parameters=["--debug", "--remote", "burcak", "local-build"],
            cwd=ogr_distgit_and_remote[0],
            return_output=True,
        )
    assert b"Remote named 'burcak' didn't exist" in ex.value.output


def test_rpm_command_for_path(ogr_distgit_and_remote):
    call_real_packit(
        parameters=["--debug", "local-build", str(ogr_distgit_and_remote[0])]
    )
    rpm_paths = Path.cwd().glob("noarch/*.rpm")
    assert all([rpm_path.exists() for rpm_path in rpm_paths])
