"""
mock webhook payload and send it to an existing packit service
"""
import pytest
import requests


@pytest.mark.skip
def test_prop_update_on_packit_020():
    url = "http://localhost:5000/webhooks/github"
    payload = {
        "repository": {
            "name": "packit",
            "html_url": "https://github.com/packit-service/packit",
            "owner": {"login": "packit-service"},
        },
        "release": {"tag_name": "0.2.0"},
    }
    response = requests.post(url=url, json=payload)
    assert response.ok
