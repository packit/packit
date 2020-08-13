# -*- coding: utf-8 -*-
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

import os
import sys
import pytest

from flexmock import flexmock
from pkg_resources import DistributionNotFound, Distribution

from packit.api import get_packit_version
from packit.exceptions import PackitException, ensure_str
from packit.utils.repo import (
    get_namespace_and_repo_name,
    git_remote_url_to_https_url,
)
from packit.utils.commands import run_command


@pytest.mark.parametrize(
    "url,namespace,repo_name",
    [
        ("https://github.com/org/name", "org", "name"),
        ("https://github.com/org/name/", "org", "name"),
        ("https://github.com/org/name.git", "org", "name"),
        ("git@github.com:org/name", "org", "name"),
        ("git@github.com:org/name.git", "org", "name"),
    ],
)
def test_get_ns_repo(url, namespace, repo_name):
    assert get_namespace_and_repo_name(url) == (namespace, repo_name)


def test_get_ns_repo_exc():
    url = "git@github.com"
    with pytest.raises(PackitException) as ex:
        get_namespace_and_repo_name(url)
    msg = f"Invalid URL format, can't obtain namespace and repository name: {url}"
    assert msg in str(ex.value)


@pytest.mark.parametrize("inp", ["/", None, ""])
def test_remote_to_https_invalid(inp):
    assert git_remote_url_to_https_url(inp) == ""


@pytest.mark.parametrize(
    "inp",
    [
        "https://github.com/packit/packit",
        "https://github.com/packit/packit.git",
        "http://github.com/packit/packit",
        "http://github.com/packit/packit.git",
        "http://www.github.com/packit/packit",
    ],
)
def test_remote_to_https_unchanged(inp):
    assert git_remote_url_to_https_url(inp) == inp


@pytest.mark.parametrize(
    "inp,ok",
    [
        ("git@github.com:packit/ogr", "https://github.com/packit/ogr"),
        (
            "ssh://ttomecek@pkgs.fedoraproject.org/rpms/alot.git",
            "https://pkgs.fedoraproject.org/rpms/alot.git",
        ),
        ("www.github.com/packit/packit", "https://www.github.com/packit/packit"),
        ("github.com/packit/packit", "https://github.com/packit/packit"),
        ("git://github.com/packit/packit", "https://github.com/packit/packit"),
        (
            "git+https://github.com/packit/packit.git",
            "https://github.com/packit/packit.git",
        ),
    ],
)
def test_remote_to_https(inp, ok):
    assert git_remote_url_to_https_url(inp) == ok


def test_run_command_w_env():
    run_command(["bash", "-c", "env | grep PATH"], env={"X": "Y"})


def test_get_packit_version_not_installed():
    flexmock(sys.modules["packit.api"]).should_receive("get_distribution").and_raise(
        DistributionNotFound
    )
    assert get_packit_version() == "NOT_INSTALLED"


def test_get_packit_version():
    flexmock(Distribution).should_receive("version").and_return("0.1.0")
    assert get_packit_version() == "0.1.0"


@pytest.mark.parametrize(
    "inp,exp",
    (("asd", "asd"), (b"asd", "asd"), ("🍺", "🍺"), (b"\xf0\x9f\x8d\xba", "🍺")),
    ids=("asd", "bytes-asd", "beer-str", "beer-bytes"),
)
def test_ensure_str(inp, exp):
    assert ensure_str(inp) == exp


@pytest.mark.parametrize(
    "to,from_,exp", (("/", "/", "."), ("/a", "/a/b", ".."), ("/a", "/c", "../a"))
)
def test_relative_to(to, from_, exp):
    assert os.path.relpath(to, from_) == exp
