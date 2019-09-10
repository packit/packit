# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

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
E2E tests which utilize cockpit projects
"""
import shutil
from pathlib import Path

import pytest

from packit.api import PackitAPI
from packit.config import get_local_package_config
from packit.local_project import LocalProject
from packit.utils import cwd
from tests.testsuite_basic.spellbook import (
    UP_OSBUILD,
    initiate_git_repo,
    get_test_config,
    build_srpm,
)


@pytest.fixture()
def osbuild(tmpdir):
    t = Path(str(tmpdir))
    u = t / "up"
    shutil.copytree(UP_OSBUILD, u)
    initiate_git_repo(u, tag="2")
    return u


def test_srpm_osbuild(osbuild):
    pc = get_local_package_config(str(osbuild))
    up_lp = LocalProject(working_dir=str(osbuild))
    c = get_test_config()
    api = PackitAPI(c, pc, up_lp)
    with cwd(osbuild):
        path = api.create_srpm()

    assert path.exists()
    build_srpm(path)
