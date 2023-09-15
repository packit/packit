# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import os
import sys
from importlib.metadata import PackageNotFoundError

import pytest
from flexmock import flexmock

from packit.api import get_packit_version
from packit.utils import sanitize_branch_name, sanitize_branch_name_for_rpm


def test_get_packit_version_not_installed():
    flexmock(sys.modules["packit.api"]).should_receive("version").and_raise(
        PackageNotFoundError
    )
    assert get_packit_version() == "NOT_INSTALLED"


def test_get_packit_version():
    flexmock(sys.modules["packit.api"]).should_receive("version").and_return("0.1.0")
    assert get_packit_version() == "0.1.0"


@pytest.mark.parametrize(
    "to,from_,exp", (("/", "/", "."), ("/a", "/a/b", ".."), ("/a", "/c", "../a"))
)
def test_relative_to(to, from_, exp):
    assert os.path.relpath(to, from_) == exp


@pytest.mark.parametrize(
    "inp,exp,exp_rpm",
    (("pr/123", "pr-123", "pr123"), ("🌈🌈🌈", "🌈🌈🌈", "🌈🌈🌈"), ("@#$#$%", "------", "")),
)
def test_sanitize_branch(inp, exp, exp_rpm):
    assert sanitize_branch_name(inp) == exp
    assert sanitize_branch_name_for_rpm(inp) == exp_rpm
