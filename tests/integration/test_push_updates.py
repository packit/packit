# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock
from munch import Munch

from packit.utils.bodhi import OurBodhiClient


@pytest.fixture()
def query_response():
    return Munch(
        {
            "updates": [
                Munch(
                    {
                        "autokarma": True,
                        "autotime": True,
                        "stable_karma": 3,
                        "stable_days": 7,
                        "unstable_karma": -3,
                        "requirements": "",
                        "require_bugs": True,
                        "require_testcases": True,
                        "display_name": "",
                        "notes": "New upstream release: 0.5.1",
                        "type": "enhancement",
                        "status": "testing",
                        "request": None,
                        "severity": "unspecified",
                        "suggest": "unspecified",
                        "locked": False,
                        "pushed": True,
                        "critpath": False,
                        "close_bugs": True,
                        "date_submitted": "2019-08-26 10:53:13",
                        "date_modified": None,
                        "date_approved": None,
                        "date_pushed": "2019-08-26 18:21:12",
                        "date_testing": "2019-08-26 18:21:12",
                        "date_stable": None,
                        "alias": "FEDORA-2019-89c99f680c",
                        "test_gating_status": "ignored",
                        "meets_testing_requirements": False,
                        "url": "https://bodhi.fedoraproject.org/updates/FEDORA-2019-89c99f680c",
                        "title": "packit-0.5.1-1.fc30",
                        "release": Munch(
                            {
                                "name": "F30",
                                "long_name": "Fedora 30",
                                "version": "30",
                                "id_prefix": "FEDORA",
                                "branch": "f30",
                                "dist_tag": "f30",
                                "stable_tag": "f30-updates",
                                "testing_tag": "f30-updates-testing",
                                "candidate_tag": "f30-updates-candidate",
                                "pending_signing_tag": "f30-signing-pending",
                                "pending_testing_tag": "f30-updates-testing-pending",
                                "pending_stable_tag": "f30-updates-pending",
                                "override_tag": "f30-override",
                                "mail_template": "fedora_errata_template",
                                "state": "current",
                                "composed_by_bodhi": True,
                                "create_automatic_updates": None,
                                "package_manager": "unspecified",
                                "testing_repository": None,
                                "composes": [],
                            }
                        ),
                        "comments": [
                            Munch(
                                {
                                    "id": 1014223,
                                    "karma": 0,
                                    "karma_critpath": 0,
                                    "text": "This update has been submitted for testing by ttomece",
                                    "timestamp": "2019-08-26 10:53:13",
                                    "update_id": 149516,
                                    "user_id": 91,
                                    "bug_feedback": [],
                                    "testcase_feedback": [],
                                    "user": Munch(
                                        {
                                            "id": 91,
                                            "name": "bodhi",
                                            "email": None,
                                            "avatar": None,
                                            "openid": "bodhi.id.fedoraproject.org",
                                            "groups": [],
                                        }
                                    ),
                                }
                            ),
                            Munch(
                                {
                                    "id": 1014224,
                                    "karma": 0,
                                    "karma_critpath": 0,
                                    "text": "This update's test gating status has been changed.",
                                    "timestamp": "2019-08-26 10:53:13",
                                    "update_id": 149516,
                                    "user_id": 91,
                                    "bug_feedback": [],
                                    "testcase_feedback": [],
                                    "user": Munch(
                                        {
                                            "id": 91,
                                            "name": "bodhi",
                                            "email": None,
                                            "avatar": None,
                                            "openid": "bodhi.id.fedoraproject.org",
                                            "groups": [],
                                        }
                                    ),
                                }
                            ),
                            Munch(
                                {
                                    "id": 1014225,
                                    "karma": 0,
                                    "karma_critpath": 0,
                                    "text": "This update's test gating status has been changed.",
                                    "timestamp": "2019-08-26 10:53:16",
                                    "update_id": 149516,
                                    "user_id": 91,
                                    "bug_feedback": [],
                                    "testcase_feedback": [],
                                    "user": Munch(
                                        {
                                            "id": 91,
                                            "name": "bodhi",
                                            "email": None,
                                            "avatar": None,
                                            "openid": "bodhi.id.fedoraproject.org",
                                            "groups": [],
                                        }
                                    ),
                                }
                            ),
                            Munch(
                                {
                                    "id": 1016059,
                                    "karma": 0,
                                    "karma_critpath": 0,
                                    "text": "This update has been pushed to testing.",
                                    "timestamp": "2019-08-27 18:22:32",
                                    "update_id": 149516,
                                    "user_id": 91,
                                    "bug_feedback": [],
                                    "testcase_feedback": [],
                                    "user": Munch(
                                        {
                                            "id": 91,
                                            "name": "bodhi",
                                            "email": None,
                                            "avatar": None,
                                            "openid": "bodhi.id.fedoraproject.org",
                                            "groups": [],
                                        }
                                    ),
                                }
                            ),
                        ],
                        "builds": [
                            Munch(
                                {
                                    "nvr": "packit-0.5.1-1.fc30",
                                    "release_id": 28,
                                    "signed": True,
                                    "type": "rpm",
                                    "epoch": 0,
                                }
                            )
                        ],
                        "compose": None,
                        "bugs": [],
                        "user": Munch(
                            {
                                "id": 754,
                                "name": "ttomecek",
                                "email": "ttomecek@redhat.com",
                                "avatar": None,
                                "openid": "ttomecek.id.fedoraproject.org",
                                "groups": [
                                    Munch({"name": "provenpackager"}),
                                    Munch({"name": "packager"}),
                                ],
                            }
                        ),
                        "updateid": "FEDORA-2019-89c99f680c",
                        "karma": 0,
                        "content_type": "rpm",
                        "test_cases": [],
                    }
                )
            ],
            "page": 1,
            "pages": 1,
        }
    )


@pytest.fixture()
def request_response():
    return Munch(
        {
            "update": Munch(
                {
                    "autokarma": True,
                    "autotime": True,
                    "stable_karma": 3,
                    "stable_days": 7,
                    "unstable_karma": -3,
                    "requirements": "",
                    "require_bugs": True,
                    "require_testcases": True,
                    "display_name": "",
                    "notes": "New upstream release: 0.5.1",
                    "type": "enhancement",
                    "status": "stable",
                    "request": None,
                    "severity": "unspecified",
                    "suggest": "unspecified",
                    "locked": False,
                    "pushed": True,
                    "critpath": False,
                    "close_bugs": True,
                    "date_submitted": "2019-08-26 10:53:13",
                    "date_modified": None,
                    "date_approved": None,
                    "date_pushed": "2019-08-26 18:21:12",
                    "date_testing": "2019-08-26 18:21:12",
                    "date_stable": "2019-09-03 08:21:12",
                    "alias": "FEDORA-2019-89c99f680c",
                    "test_gating_status": "ignored",
                    "meets_testing_requirements": False,
                    "url": "https://bodhi.fedoraproject.org/updates/FEDORA-2019-89c99f680c",
                    "title": "packit-0.5.1-1.fc30",
                    "release": Munch(
                        {
                            "name": "F30",
                            "long_name": "Fedora 30",
                            "version": "30",
                            "id_prefix": "FEDORA",
                            "branch": "f30",
                            "dist_tag": "f30",
                            "stable_tag": "f30-updates",
                            "testing_tag": "f30-updates-testing",
                            "candidate_tag": "f30-updates-candidate",
                            "pending_signing_tag": "f30-signing-pending",
                            "pending_testing_tag": "f30-updates-testing-pending",
                            "pending_stable_tag": "f30-updates-pending",
                            "override_tag": "f30-override",
                            "mail_template": "fedora_errata_template",
                            "state": "current",
                            "composed_by_bodhi": True,
                            "create_automatic_updates": None,
                            "package_manager": "unspecified",
                            "testing_repository": None,
                            "composes": [],
                        }
                    ),
                    "comments": [
                        Munch(
                            {
                                "id": 1014223,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been submitted for testing by ttomecek. ",
                                "timestamp": "2019-08-26 10:53:13",
                                "update_id": 149516,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "avatar": None,
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 1014224,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update's test gating status has been changed.",
                                "timestamp": "2019-08-26 10:53:13",
                                "update_id": 149516,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "avatar": None,
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 1014225,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update's test gating status has been changed.",
                                "timestamp": "2019-08-26 10:53:16",
                                "update_id": 149516,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "avatar": None,
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 1016059,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been pushed to testing.",
                                "timestamp": "2019-08-27 18:22:32",
                                "update_id": 149516,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "avatar": None,
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                    ],
                    "builds": [
                        Munch(
                            {
                                "nvr": "packit-0.5.1-1.fc30",
                                "release_id": 28,
                                "signed": True,
                                "type": "rpm",
                                "epoch": 0,
                            }
                        )
                    ],
                    "compose": None,
                    "bugs": [],
                    "user": Munch(
                        {
                            "id": 754,
                            "name": "ttomecek",
                            "email": "ttomecek@redhat.com",
                            "avatar": None,
                            "openid": "ttomecek.id.fedoraproject.org",
                            "groups": [
                                Munch({"name": "provenpackager"}),
                                Munch({"name": "packager"}),
                            ],
                        }
                    ),
                    "updateid": "FEDORA-2019-89c99f680c",
                    "karma": 0,
                    "content_type": "rpm",
                    "test_cases": [],
                }
            )
        }
    )


def test_push_updates(
    cwd_upstream_or_distgit, api_instance, query_response, request_response
):
    from bodhi.client.bindings import BodhiClient

    u, d, api = api_instance

    flexmock(BodhiClient)
    BodhiClient.should_receive("query").and_return(query_response).once()
    BodhiClient.should_receive("request").with_args(
        update="FEDORA-2019-89c99f680c", request="stable"
    ).and_return(request_response).once()

    flexmock(
        OurBodhiClient,
        ensure_auth=lambda: None,  # this is where the browser/OIDC fun happens
        login_with_kerberos=lambda: None,
    )

    api.push_updates()
