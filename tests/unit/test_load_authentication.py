# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

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
    "key",
    dep_keys,
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
