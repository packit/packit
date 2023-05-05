# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import pytest
from flexmock import flexmock

from packit.exceptions import PackitException
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
            }
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
        "POST", "compose", payload=payload
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
    """Test that refreshing with no token fails properly"""
    flexmock(ImageBuilder).should_receive("_get_access_token").and_return(None)
    with pytest.raises(PackitException) as exc:
        ImageBuilder(None)
    assert (
        "Unable to obtain access token. You may need to regenerate the refresh token."
        in str(exc)
    )
