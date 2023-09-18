# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import logging

import pytest
from flexmock import flexmock
from requests import HTTPError, Session

from packit.exceptions import ImageBuilderError, PackitException
from packit.vm_image_build import ImageBuilder


def test_create_image():
    """Test creating an image"""
    # auth is tested in tests_recording
    flexmock(ImageBuilder).should_receive("refresh_auth").and_return(None)
    ib = ImageBuilder("foo-token")
    payload = {
        "image_name": "mona-lisa",
        "distribution": "rhel-90",
        "image_requests": [
            {
                "architecture": "x86_64",
                "image_type": "aws",
                "upload_request": {
                    "options": {"share_with_accounts": ["123456789012"]},
                    "type": "aws",
                },
            },
        ],
        "customizations": {
            "payload_repositories": [
                {
                    "rhsm": False,
                    "baseurl": "https://copr.fedoraproject.org/coprs/foo/bar/",
                    "check_gpg": False,
                },
            ],
            "packages": ["mona-lisa"],
        },
    }
    request_response = {"id": "foo-baz-bar"}
    flexmock(ib).should_receive("image_builder_request").with_args(
        "POST",
        "compose",
        payload=payload,
    ).and_return(flexmock(json=lambda: request_response))
    response = ib.create_image(
        "rhel-90",
        "mona-lisa",
        {
            "architecture": "x86_64",
            "image_type": "aws",
            "upload_request": {
                "options": {"share_with_accounts": ["123456789012"]},
                "type": "aws",
            },
        },
        {"packages": ["mona-lisa"]},
        "https://copr.fedoraproject.org/coprs/foo/bar/",
    )
    assert response == "foo-baz-bar"


def test_refresh_fails():
    """Refereshing console.rh.c access token should have sensible experience"""
    # We generate refresh token in the webui for packit and then use it to generate access token
    # Refresh token can expire: when that happens, all requests end with 401
    # Before this commit, we did not expect that to happen
    # The traceback we got took us some time to figure out what's happening exactly
    # This test ensures that Packit raises sensible exception when access token cannot be obtained
    flexmock(ImageBuilder).should_receive("_get_access_token").and_return(None)
    with pytest.raises(PackitException) as exc:
        ImageBuilder("this-token-definitely-not-works-unless...")
        assert (
            "Unable to obtain access token. You may need to regenerate the refresh token."
            in str(exc)
        )


def test_bad_request(caplog):
    def _raise_for_status(*args, **_):
        raise HTTPError()

    response_json = {
        "errors": [
            {
                "detail": (
                    "request body has an error: doesn't match schema... "
                    'value "fedora-rawhide" is not one of the allowed values'
                ),
            },
        ],
    }

    r = flexmock(
        ok=False,
        status_code=400,
        text=str(response_json),
        raise_for_status=_raise_for_status,
    )
    flexmock(ImageBuilder).should_receive("refresh_auth").and_return(None)
    flexmock(Session).should_receive("request").and_return(r)
    with caplog.at_level(logging.INFO, logger="packit"):
        ib = ImageBuilder("foobar")
        with pytest.raises(ImageBuilderError):
            ib.create_image("fedora-rawhide", "foo-bar", {}, {}, "")
        assert "request body has an error" in caplog.text
        assert 'value "fedora-rawhide" is not one of the allowed values' in caplog.text
