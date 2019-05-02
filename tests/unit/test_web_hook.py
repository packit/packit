from flexmock import flexmock
from flask import Flask, request
import pytest

from packit.config import Config
from packit.service.web_hook import _validate_signature


@pytest.mark.parametrize(
    "digest, is_good",
    [
        # hmac.new(webhook_secret, msg=payload, digestmod=hashlib.sha1).hexdigest()
        ("4e0281ef362383a2ab30c9dde79167da3b300b58", True),
        ("abcdefghijklmnopqrstuvqxyz", False),
    ],
)
def test_validate_signature(digest, is_good):
    payload = b'{"zen": "Keep it logically awesome."}'
    webhook_secret = "testing-secret"
    headers = {"X-Hub-Signature": f"sha1={digest}"}

    config = flexmock(Config)
    config.webhook_secret = webhook_secret
    with Flask(__name__).test_request_context():
        request._cached_data = request.data = payload
        request.headers = headers
        assert _validate_signature(config) is is_good
