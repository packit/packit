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
from pathlib import Path

import pytest

from packit.cli.utils import get_packit_api
from packit.local_project import LocalProject
from packit.utils import cwd
from tests.spellbook import (
    initiate_git_repo,
    get_test_config,
    UP_SNAPD,
    UP_OSBUILD,
    UP_EDD,
    DG_OGR,
    build_srpm,
    UP_VSFTPD,
)


@pytest.fixture(
    params=[
        (UP_SNAPD, "2.41", "https://github.com/snapcore/snapd"),
        (UP_OSBUILD, "2", "https://github.com/osbuild/osbuild"),
        (UP_EDD, "0.3", "https://github.com/psss/edd"),
        (UP_VSFTPD, "3.0.3", "https://github.com/olysonek/vsftpd"),
        (DG_OGR, None, "https://src.fedoraproject.org/rpms/python-ogr"),
    ]
)
def example_repo(request, tmpdir):
    example_path, tag, remote = request.param
    t = Path(str(tmpdir))
    u = t / "up"
    initiate_git_repo(u, tag=tag, copy_from=example_path, upstream_remote=remote)
    return u


def test_srpm_on_example(example_repo):
    c = get_test_config()
    api = get_packit_api(
        config=c, local_project=LocalProject(working_dir=str(example_repo))
    )
    with cwd(example_repo):
        path = api.create_srpm()
    assert path.exists()
    build_srpm(path)
