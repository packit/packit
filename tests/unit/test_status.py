# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from flexmock import flexmock

from packit.status import Status
from packit.utils.bodhi import OurBodhiClient


def test_status_updates(config_mock, package_config_mock, upstream_mock, distgit_mock):
    flexmock(
        OurBodhiClient,
        query=lambda packages, page: {
            "updates": [
                {
                    "title": "python-requre-0.8.1-2.fc33",
                    "karma": 2,
                    "status": "stable",
                    "release": {"branch": "f33"},
                },
                {
                    "title": "python-requre-0.8.1-2.fc34",
                    "karma": 3,
                    "status": "stable",
                    "release": {"branch": "f34"},
                },
            ],
            "page": 1,
            "pages": 1,
        },
    )

    status = Status(config_mock, package_config_mock, upstream_mock, distgit_mock)
    table = status.get_updates()
    assert table == [
        ["python-requre-0.8.1-2.fc33", 2, "stable"],
        ["python-requre-0.8.1-2.fc34", 3, "stable"],
    ]
