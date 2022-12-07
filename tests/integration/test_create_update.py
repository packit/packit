# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
import koji
from bodhi.client.bindings import BodhiClientException
from flexmock import flexmock
from munch import Munch

from packit import distgit
from packit.exceptions import PackitBodhiException
from packit.utils.bodhi import OurBodhiClient


@pytest.fixture()
def bodhi_response():
    return Munch(
        {
            "title": "sen-0.6.1-1.fc30",
            "autokarma": True,
            "stable_karma": 3,
            "unstable_karma": -3,
            "requirements": "",
            "require_bugs": True,
            "require_testcases": True,
            "display_name": "",
            "notes": "New upstream release: 0.6.1",
            "type": "enhancement",
            "status": "testing",
            "request": "stable",
            "severity": "unspecified",
            "suggest": "unspecified",
            "locked": False,
            "pushed": True,
            "critpath": False,
            "close_bugs": True,
            "date_submitted": "2019-03-10 12:09:35",
            "date_modified": None,
            "date_approved": None,
            "date_pushed": "2019-03-10 16:08:18",
            "date_testing": "2019-03-10 16:08:18",
            "date_stable": None,
            "alias": "FEDORA-2019-0c53f2476d",
            "old_updateid": None,
            "test_gating_status": "ignored",
            "greenwave_summary_string": "no tests are required",
            "greenwave_unsatisfied_requirements": None,
            "meets_testing_requirements": True,
            "url": "https://bodhi.fedoraproject.org/updates/FEDORA-2019-0c53f2476d",
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
                    "state": "pending",
                    "composed_by_bodhi": True,
                    "composes": [],
                }
            ),
            "comments": [
                Munch(
                    {
                        "id": 905816,
                        "karma": 0,
                        "karma_critpath": 0,
                        "text": "This update has been submitted for testing by ttomecek. ",
                        "anonymous": False,
                        "timestamp": "2019-03-10 12:09:35",
                        "update_id": 133306,
                        "user_id": 91,
                        "bug_feedback": [],
                        "testcase_feedback": [],
                        "user": Munch(
                            {
                                "id": 91,
                                "name": "bodhi",
                                "email": None,
                                "show_popups": True,
                                "avatar": "https://apps.fedoraproject.org/"
                                "img/icons/bodhi-24.png",
                                "openid": "bodhi.id.fedoraproject.org",
                                "groups": [],
                            }
                        ),
                    }
                ),
                Munch(
                    {
                        "id": 905871,
                        "karma": 0,
                        "karma_critpath": 0,
                        "text": "This update has been pushed to testing.",
                        "anonymous": False,
                        "timestamp": "2019-03-10 16:08:34",
                        "update_id": 133306,
                        "user_id": 91,
                        "bug_feedback": [],
                        "testcase_feedback": [],
                        "user": Munch(
                            {
                                "id": 91,
                                "name": "bodhi",
                                "email": None,
                                "show_popups": True,
                                "avatar": "https://apps.fedoraproject.org/"
                                "img/icons/bodhi-24.png",
                                "openid": "bodhi.id.fedoraproject.org",
                                "groups": [],
                            }
                        ),
                    }
                ),
                Munch(
                    {
                        "id": 908106,
                        "karma": 0,
                        "karma_critpath": 0,
                        "text": "This update has reached 3 days in testing"
                        " and can be pushed to stable now if the maintainer wishes",
                        "anonymous": False,
                        "timestamp": "2019-03-13 18:02:58",
                        "update_id": 133306,
                        "user_id": 91,
                        "bug_feedback": [],
                        "testcase_feedback": [],
                        "user": Munch(
                            {
                                "id": 91,
                                "name": "bodhi",
                                "email": None,
                                "show_popups": True,
                                "avatar": "https://apps.fedoraproject.org/"
                                "img/icons/bodhi-24.png",
                                "openid": "bodhi.id.fedoraproject.org",
                                "groups": [],
                            }
                        ),
                    }
                ),
                Munch(
                    {
                        "id": 908350,
                        "karma": 0,
                        "karma_critpath": 0,
                        "text": "This update has been submitted for batched by ttomecek. ",
                        "anonymous": False,
                        "timestamp": "2019-03-14 07:47:14",
                        "update_id": 133306,
                        "user_id": 91,
                        "bug_feedback": [],
                        "testcase_feedback": [],
                        "user": Munch(
                            {
                                "id": 91,
                                "name": "bodhi",
                                "email": None,
                                "show_popups": True,
                                "avatar": "https://apps.fedoraproject.org/"
                                "img/icons/bodhi-24.png",
                                "openid": "bodhi.id.fedoraproject.org",
                                "groups": [],
                            }
                        ),
                    }
                ),
                Munch(
                    {
                        "id": 908675,
                        "karma": 0,
                        "karma_critpath": 0,
                        "text": "This update has been submitted for stable by bodhi. ",
                        "anonymous": False,
                        "timestamp": "2019-03-14 23:45:38",
                        "update_id": 133306,
                        "user_id": 91,
                        "bug_feedback": [],
                        "testcase_feedback": [],
                        "user": Munch(
                            {
                                "id": 91,
                                "name": "bodhi",
                                "email": None,
                                "show_popups": True,
                                "avatar": "https://apps.fedoraproject.org/"
                                "img/icons/bodhi-24.png",
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
                        "nvr": "sen-0.6.1-1.fc30",
                        "release_id": 28,
                        "signed": True,
                        "ci_url": None,
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
                    "show_popups": True,
                    "avatar": "https://seccdn.libravatar.org/avatar/"
                    "2098fd3a827c38e855bd76b1f6b75c85483b11"
                    "2f0e8f086257309df75dc04dc0?s=24&d=retro",
                    "openid": "ttomecek.id.fedoraproject.org",
                    "groups": [
                        Munch({"name": "provenpackager"}),
                        Munch({"name": "packager"}),
                    ],
                }
            ),
            "updateid": "FEDORA-2019-0c53f2476d",
            "submitter": "ttomecek",
            "karma": 0,
            "content_type": "rpm",
            "test_cases": [],
        }
    )


@pytest.fixture()
def latest_builds_from_koji():
    return [
        {"nvr": "sen-0.6.1-1.fc30"},
    ]


@pytest.mark.parametrize(
    "branch,update_type,update_notes,koji_builds",
    (
        (
            "f30",
            "enhancement",
            "This is the best upstream release ever: {version}",
            ("foo-1-1",),
        ),
        (
            "f30",
            "enhancement",
            "This is the best upstream release ever: {version}",
            None,
        ),
    ),
)
def test_basic_bodhi_update(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
    branch,
    update_type,
    update_notes,
    koji_builds,
    bodhi_response,
    latest_builds_from_koji,
):
    u, d, api = api_instance
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()

    flexmock(koji.ClientSession).should_receive("__getattr__").and_return(
        lambda tag, package, inherit, latest, strict: latest_builds_from_koji
    )

    flexmock(
        OurBodhiClient,
        save=lambda **kwargs: bodhi_response,
        ensure_auth=lambda: None,  # this is where the browser/OIDC fun happens
        login_with_kerberos=lambda: None,
    )

    api.create_update(
        dist_git_branch=branch,
        update_type=update_type,
        update_notes=update_notes,
        koji_builds=koji_builds,
    )


@pytest.mark.parametrize(
    "update_notes,koji_builds",
    (
        (
            "This is the best upstream release ever: {version}",
            ("foo-1-1",),
        ),
        (
            "This is the best upstream release ever: {version}",
            None,
        ),
    ),
)
def test_bodhi_update_with_bugs(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
    update_notes,
    koji_builds,
    bodhi_response,
    latest_builds_from_koji,
):
    """This test checks that bugzilla IDs can be passed and that bodhi
    authentication works using kerberos."""

    def validate_save(kwargs, expected_kwargs):
        assert kwargs == expected_kwargs
        return bodhi_response

    u, d, api = api_instance
    api.config.fas_user = "packit"
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()

    flexmock(koji.ClientSession).should_receive("__getattr__").and_return(
        lambda tag, package, inherit, latest, strict: latest_builds_from_koji
    )

    flexmock(
        OurBodhiClient,
        latest_builds=lambda package: latest_builds_from_koji,
        save=lambda **kwargs: validate_save(
            kwargs,
            {
                "builds": koji_builds or [latest_builds_from_koji[0]["nvr"]],
                "notes": update_notes.format(version="0.0.0"),
                "type": "enhancement",
                "bugs": ["1", "2", "3"],
            },
        ),
        ensure_auth=lambda: None,
        login_with_kerberos=lambda: None,
    )
    flexmock(OurBodhiClient).should_receive("login_with_kerberos").and_return(None)

    api.create_update(
        dist_git_branch="f30",
        update_type="enhancement",
        update_notes=update_notes,
        koji_builds=koji_builds,
        bugzilla_ids=[1, 2, 3],
    )


def test_bodhi_update_auth_with_fas(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
    bodhi_response,
    latest_builds_from_koji,
):
    u, d, api = api_instance
    api.config.fas_user = "the_fas_username"
    api.config.fas_password = "the_fas_password"
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()

    flexmock(distgit).should_call("get_bodhi_client").with_args(
        fas_username="the_fas_username",
        fas_password="the_fas_password",
        kerberos_realm="FEDORAPROJECT.ORG",
    )
    flexmock(
        OurBodhiClient,
        latest_builds=lambda package: latest_builds_from_koji,
        save=lambda **kwargs: bodhi_response,
        ensure_auth=lambda: None,
        login_with_kerberos=lambda: None,
    )

    api.create_update(
        dist_git_branch="f30",
        update_type="enhancement",
        update_notes="This is the best upstream release ever: {version}",
        koji_builds=("foo-1-1",),
    )


def test_bodhi_update_fails(
    cwd_upstream,
    api_instance,
    mock_remote_functionality_upstream,
):
    """This test checks that bugzilla IDs can be passed and that bodhi
    authentication works using kerberos."""
    build_nvr = "python-specfile-0.10.0-1.fc37"

    u, d, api = api_instance
    api.config.fas_user = "packit"
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()

    flexmock(
        OurBodhiClient,
        ensure_auth=lambda: None,
        login_with_kerberos=lambda: None,
    )
    flexmock(OurBodhiClient).should_receive("login_with_kerberos").and_return(None)
    flexmock(OurBodhiClient).should_receive("save").and_raise(
        BodhiClientException,
        {
            "status": "error",
            "errors": [
                {
                    "location": "body",
                    "name": "builds",
                    "description": "Cannot find any tags associated with build: "
                    "python-specfile-0.10.0-1.fc37",
                },
                {
                    "location": "body",
                    "name": "builds",
                    "description": "Cannot find release associated with build: "
                    "python-specfile-0.10.0-1.fc37",
                    "tags": [],
                },
            ],
        },
    )

    with pytest.raises(PackitBodhiException) as ex:
        api.create_update(
            dist_git_branch="f37",
            update_type="enhancement",
            update_notes="asd",
            koji_builds=[build_nvr],
        )
    assert str(ex.value).startswith("There is a problem with creating a bodhi update")
