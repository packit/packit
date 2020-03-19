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

import logging

import pytest
from packit.config.config import Config

logger = logging.getLogger(__name__)

dep_keys = [
    "github_app_id",
    "github_app_cert_path",
    "github_token",
    "pagure_user_token",
    "pagure_instance_url",
    "pagure_fork_token",
]

authentication = {
    "authentication": {
        "github.com": {"token": "abcd"},
        "pagure": {"token": "abcd", "instance_url": "https://src.fedoraproject.org"},
    }
}


@pytest.mark.parametrize(
    "key", dep_keys,
)
def test_with_deprecated_keys(key, caplog, recwarn):
    raw_dict = {key: "somevalue"}
    Config.load_authentication(raw_dict)
    assert "Please, use 'authentication' key in the user" in caplog.text
    caplog.clear()


def test_with_only_authentication(caplog, recwarn):
    Config.load_authentication(authentication)
    assert "Please, use 'authentication' key in the user" not in caplog.text


def test_with_both_authentication(caplog, recwarn):
    raw_dict = authentication
    raw_dict[dep_keys[3]] = "somevalue"
    Config.load_authentication(raw_dict)
    assert "Please, use 'authentication' key in the user" not in caplog.text
