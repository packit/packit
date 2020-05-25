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

import pytest
from flexmock import flexmock
from munch import Munch

from tests.spellbook import can_a_module_be_imported


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


# FIXME: https://github.com/fedora-infra/bodhi/issues/3058
@pytest.mark.skipif(
    not can_a_module_be_imported("bodhi"), reason="bodhi not present, skipping"
)
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
):
    # https://github.com/fedora-infra/bodhi/issues/3058
    from bodhi.client.bindings import BodhiClient

    u, d, api = api_instance
    flexmock(api).should_receive("init_kerberos_ticket").at_least().once()

    flexmock(
        BodhiClient,
        latest_builds=lambda package: {
            "f29-override": "sen-0.6.0-3.fc29",
            "f29-updates": "sen-0.6.0-3.fc29",
            "f29-updates-candidate": "sen-0.6.0-3.fc29",
            "f29-updates-pending": "sen-0.6.0-3.fc29",
            "f29-updates-testing": "sen-0.6.0-3.fc29",
            "f29-updates-testing-pending": "sen-0.6.0-3.fc29",
            "f30-override": "sen-0.6.0-4.fc30",
            "f30-updates": "sen-0.6.0-4.fc30",
            "f30-updates-candidate": "sen-0.6.1-1.fc30",
            "f30-updates-pending": "sen-0.6.0-4.fc30",
            "f30-updates-testing": "sen-0.6.0-4.fc30",
            "f30-updates-testing-pending": "sen-0.6.0-4.fc30",
        },
        save=lambda **kwargs: bodhi_response,
    )

    api.create_update(
        dist_git_branch=branch,
        update_type=update_type,
        update_notes=update_notes,
        koji_builds=koji_builds,
    )
