# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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

from munch import Munch

BODHI_UPDATES = Munch(
    {
        "updates": [
            Munch(
                {
                    "title": "colin-0.3.1-1.fc29",
                    "autokarma": True,
                    "stable_karma": 3,
                    "unstable_karma": -3,
                    "requirements": "",
                    "require_bugs": True,
                    "require_testcases": True,
                    "display_name": "",
                    "notes": "new upstream release\n\n----\n\nlatest upstream "
                    "release\n\n----\n\nUpdate to latest upstream release.",
                    "type": "enhancement",
                    "status": "stable",
                    "request": None,
                    "severity": "unspecified",
                    "suggest": "unspecified",
                    "locked": False,
                    "pushed": True,
                    "critpath": False,
                    "close_bugs": True,
                    "date_submitted": "2019-01-21 16:51:00",
                    "date_modified": None,
                    "date_approved": None,
                    "date_pushed": "2019-01-30 02:06:12",
                    "date_testing": "2019-01-22 03:03:10",
                    "date_stable": "2019-01-30 02:06:12",
                    "alias": "FEDORA-2019-7006fbed73",
                    "old_updateid": None,
                    "test_gating_status": "ignored",
                    "greenwave_summary_string": "no tests are required",
                    "greenwave_unsatisfied_requirements": None,
                    "meets_testing_requirements": True,
                    "url": "https://bodhi.fedoraproject.org/updates/FEDORA-2019-7006fbed73",
                    "release": Munch(
                        {
                            "name": "F29",
                            "long_name": "Fedora 29",
                            "version": "29",
                            "id_prefix": "FEDORA",
                            "branch": "f29",
                            "dist_tag": "f29",
                            "stable_tag": "f29-updates",
                            "testing_tag": "f29-updates-testing",
                            "candidate_tag": "f29-updates-candidate",
                            "pending_signing_tag": "f29-signing-pending",
                            "pending_testing_tag": "f29-updates-testing-pending",
                            "pending_stable_tag": "f29-updates-pending",
                            "override_tag": "f29-override",
                            "mail_template": "fedora_errata_template",
                            "state": "current",
                            "composed_by_bodhi": True,
                            "composes": [],
                        }
                    ),
                    "comments": [
                        Munch(
                            {
                                "id": 886725,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been submitted "
                                "for testing by ttomecek. ",
                                "anonymous": False,
                                "timestamp": "2019-01-21 16:51:00",
                                "update_id": 130273,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 886729,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has obsoleted [colin-0.3.0-2.fc29]"
                                "(https://bodhi.fedoraproject.org/updates/"
                                "FEDORA-2019-f921969692), and has inherited "
                                "its bugs and notes.",
                                "anonymous": False,
                                "timestamp": "2019-01-21 16:51:03",
                                "update_id": 130273,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 886745,
                                "karma": 1,
                                "karma_critpath": 0,
                                "text": "Works well, thanks!\n\n(tested with "
                                "registry.fedoraproject.org/fedora:29 image)",
                                "anonymous": False,
                                "timestamp": "2019-01-21 18:09:32",
                                "update_id": 130273,
                                "user_id": 4222,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 4222,
                                        "name": "lachmanfrantisek",
                                        "email": "flachman@redhat.com",
                                        "show_popups": True,
                                        "avatar": "https://seccdn.libravatar.org/avatar/"
                                        "38deedcf02e4617a9a8a0c04b67fd4c7fcea9"
                                        "ededf02d13a93a7626477350e45?s=24&d=retro",
                                        "openid": "lachmanfrantisek.id.fedoraproject.org",
                                        "groups": [Munch({"name": "packager"})],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 886940,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been pushed to testing.",
                                "anonymous": False,
                                "timestamp": "2019-01-22 03:04:32",
                                "update_id": 130273,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 889233,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has reached 7 days in testing "
                                "and can be pushed to stable now "
                                "if the maintainer wishes",
                                "anonymous": False,
                                "timestamp": "2019-01-29 06:00:45",
                                "update_id": 130273,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 889253,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been submitted "
                                "for batched by ttomecek.",
                                "anonymous": False,
                                "timestamp": "2019-01-29 08:41:38",
                                "update_id": 130273,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 889436,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been submitted for stable by bodhi. ",
                                "anonymous": False,
                                "timestamp": "2019-01-29 23:45:40",
                                "update_id": 130273,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 889521,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been pushed to stable.",
                                "anonymous": False,
                                "timestamp": "2019-01-30 02:07:18",
                                "update_id": 130273,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
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
                                "nvr": "colin-0.3.1-1.fc29",
                                "release_id": 23,
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
                            "2098fd3a827c38e855bd76b1f6b75c85483b1"
                            "12f0e8f086257309df75dc04dc0?s=24&d=retro",
                            "openid": "ttomecek.id.fedoraproject.org",
                            "groups": [
                                Munch({"name": "provenpackager"}),
                                Munch({"name": "packager"}),
                            ],
                        }
                    ),
                    "updateid": "FEDORA-2019-7006fbed73",
                    "submitter": "ttomecek",
                    "karma": 1,
                    "content_type": "rpm",
                    "test_cases": [],
                }
            ),
            Munch(
                {
                    "title": "colin-0.3.1-1.fc28",
                    "autokarma": True,
                    "stable_karma": 3,
                    "unstable_karma": -3,
                    "requirements": "",
                    "require_bugs": True,
                    "require_testcases": True,
                    "display_name": "",
                    "notes": "new upstream release\n\n----\n\nlatest upstream "
                    "release\n\n----\n\nUpdate to latest upstream release.",
                    "type": "enhancement",
                    "status": "stable",
                    "request": None,
                    "severity": "unspecified",
                    "suggest": "unspecified",
                    "locked": False,
                    "pushed": True,
                    "critpath": False,
                    "close_bugs": True,
                    "date_submitted": "2019-01-21 16:50:59",
                    "date_modified": None,
                    "date_approved": None,
                    "date_pushed": "2019-01-30 01:31:27",
                    "date_testing": "2019-01-22 01:16:27",
                    "date_stable": "2019-01-30 01:31:27",
                    "alias": "FEDORA-2019-cb1e057344",
                    "old_updateid": None,
                    "test_gating_status": "ignored",
                    "greenwave_summary_string": "no tests are required",
                    "greenwave_unsatisfied_requirements": None,
                    "meets_testing_requirements": True,
                    "url": "https://bodhi.fedoraproject.org/updates/FEDORA-2019-cb1e057344",
                    "release": Munch(
                        {
                            "name": "F28",
                            "long_name": "Fedora 28",
                            "version": "28",
                            "id_prefix": "FEDORA",
                            "branch": "f28",
                            "dist_tag": "f28",
                            "stable_tag": "f28-updates",
                            "testing_tag": "f28-updates-testing",
                            "candidate_tag": "f28-updates-candidate",
                            "pending_signing_tag": "f28-signing-pending",
                            "pending_testing_tag": "f28-updates-testing-pending",
                            "pending_stable_tag": "f28-updates-pending",
                            "override_tag": "f28-override",
                            "mail_template": "fedora_errata_template",
                            "state": "current",
                            "composed_by_bodhi": True,
                            "composes": [],
                        }
                    ),
                    "comments": [
                        Munch(
                            {
                                "id": 886724,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been submitted "
                                "for testing by ttomecek. ",
                                "anonymous": False,
                                "timestamp": "2019-01-21 16:50:59",
                                "update_id": 130272,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 886727,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has obsoleted [colin-0.3.0-2.fc28]"
                                "(https://bodhi.fedoraproject.org/updates/"
                                "FEDORA-2019-7223843531), and has inherited "
                                "its bugs and notes.",
                                "anonymous": False,
                                "timestamp": "2019-01-21 16:51:02",
                                "update_id": 130272,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 886744,
                                "karma": 1,
                                "karma_critpath": 0,
                                "text": "Works well, thanks!\n\n(tested with "
                                "registry.fedoraproject.org/fedora:28 image)",
                                "anonymous": False,
                                "timestamp": "2019-01-21 18:08:52",
                                "update_id": 130272,
                                "user_id": 4222,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 4222,
                                        "name": "lachmanfrantisek",
                                        "email": "flachman@redhat.com",
                                        "show_popups": True,
                                        "avatar": "https://seccdn.libravatar.org/avatar/"
                                        "38deedcf02e4617a9a8a0c04b67fd4c7fcea9"
                                        "ededf02d13a93a7626477350e45?s=24&d=retro",
                                        "openid": "lachmanfrantisek.id.fedoraproject.org",
                                        "groups": [Munch({"name": "packager"})],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 886870,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been pushed to testing.",
                                "anonymous": False,
                                "timestamp": "2019-01-22 01:17:03",
                                "update_id": 130272,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 889232,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has reached 7 days in testing "
                                "and can be pushed to stable now "
                                "if the maintainer wishes",
                                "anonymous": False,
                                "timestamp": "2019-01-29 06:00:44",
                                "update_id": 130272,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 889254,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been submitted for "
                                "batched by ttomecek. ",
                                "anonymous": False,
                                "timestamp": "2019-01-29 08:41:41",
                                "update_id": 130272,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 889435,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been submitted for stable by bodhi. ",
                                "anonymous": False,
                                "timestamp": "2019-01-29 23:45:39",
                                "update_id": 130272,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 889457,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been pushed to stable.",
                                "anonymous": False,
                                "timestamp": "2019-01-30 01:32:23",
                                "update_id": 130272,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
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
                                "nvr": "colin-0.3.1-1.fc28",
                                "release_id": 21,
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
                            "2098fd3a827c38e855bd76b1f6b75c85483b1"
                            "12f0e8f086257309df75dc04dc0?s=24&d=retro",
                            "openid": "ttomecek.id.fedoraproject.org",
                            "groups": [
                                Munch({"name": "provenpackager"}),
                                Munch({"name": "packager"}),
                            ],
                        }
                    ),
                    "updateid": "FEDORA-2019-cb1e057344",
                    "submitter": "ttomecek",
                    "karma": 1,
                    "content_type": "rpm",
                    "test_cases": [],
                }
            ),
            Munch(
                {
                    "title": "colin-0.3.0-2.fc28",
                    "autokarma": True,
                    "stable_karma": 3,
                    "unstable_karma": -3,
                    "requirements": "",
                    "require_bugs": True,
                    "require_testcases": True,
                    "display_name": "",
                    "notes": "latest upstream release\n\n----\n\nUpdate to "
                    "latest upstream release.",
                    "type": "enhancement",
                    "status": "obsolete",
                    "request": None,
                    "severity": "unspecified",
                    "suggest": "unspecified",
                    "locked": False,
                    "pushed": False,
                    "critpath": False,
                    "close_bugs": True,
                    "date_submitted": "2019-01-18 10:38:22",
                    "date_modified": None,
                    "date_approved": None,
                    "date_pushed": "2019-01-19 01:43:21",
                    "date_testing": "2019-01-19 01:43:21",
                    "date_stable": None,
                    "alias": "FEDORA-2019-7223843531",
                    "old_updateid": None,
                    "test_gating_status": "ignored",
                    "greenwave_summary_string": "no tests are required",
                    "greenwave_unsatisfied_requirements": None,
                    "meets_testing_requirements": True,
                    "url": "https://bodhi.fedoraproject.org/updates/FEDORA-2019-7223843531",
                    "release": Munch(
                        {
                            "name": "F28",
                            "long_name": "Fedora 28",
                            "version": "28",
                            "id_prefix": "FEDORA",
                            "branch": "f28",
                            "dist_tag": "f28",
                            "stable_tag": "f28-updates",
                            "testing_tag": "f28-updates-testing",
                            "candidate_tag": "f28-updates-candidate",
                            "pending_signing_tag": "f28-signing-pending",
                            "pending_testing_tag": "f28-updates-testing-pending",
                            "pending_stable_tag": "f28-updates-pending",
                            "override_tag": "f28-override",
                            "mail_template": "fedora_errata_template",
                            "state": "current",
                            "composed_by_bodhi": True,
                            "composes": [],
                        }
                    ),
                    "comments": [
                        Munch(
                            {
                                "id": 885830,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been submitted "
                                "for testing by ttomecek. ",
                                "anonymous": False,
                                "timestamp": "2019-01-18 10:38:22",
                                "update_id": 130128,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 885834,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has obsoleted [colin-0.2.1-1.fc28]"
                                "(https://bodhi.fedoraproject.org/updates/"
                                "FEDORA-2018-507426b4b6), "
                                "and has inherited its bugs and notes.",
                                "anonymous": False,
                                "timestamp": "2019-01-18 10:38:25",
                                "update_id": 130128,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 886062,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been pushed to testing.",
                                "anonymous": False,
                                "timestamp": "2019-01-19 01:44:06",
                                "update_id": 130128,
                                "user_id": 91,
                                "bug_feedback": [],
                                "testcase_feedback": [],
                                "user": Munch(
                                    {
                                        "id": 91,
                                        "name": "bodhi",
                                        "email": None,
                                        "show_popups": True,
                                        "avatar": "https://apps.fedoraproject.org/img/"
                                        "icons/bodhi-24.png",
                                        "openid": "bodhi.id.fedoraproject.org",
                                        "groups": [],
                                    }
                                ),
                            }
                        ),
                        Munch(
                            {
                                "id": 886726,
                                "karma": 0,
                                "karma_critpath": 0,
                                "text": "This update has been obsoleted by [colin-0.3.1-1.fc28]"
                                "(https://bodhi.fedoraproject.org/updates/"
                                "FEDORA-2019-cb1e057344).",
                                "anonymous": False,
                                "timestamp": "2019-01-21 16:51:02",
                                "update_id": 130128,
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
                                "nvr": "colin-0.3.0-2.fc28",
                                "release_id": 21,
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
                            "2098fd3a827c38e855bd76b1f6b75c85483b112"
                            "f0e8f086257309df75dc04dc0?s=24&d=retro",
                            "openid": "ttomecek.id.fedoraproject.org",
                            "groups": [
                                Munch({"name": "provenpackager"}),
                                Munch({"name": "packager"}),
                            ],
                        }
                    ),
                    "updateid": "FEDORA-2019-7223843531",
                    "submitter": "ttomecek",
                    "karma": 0,
                    "content_type": "rpm",
                    "test_cases": [],
                }
            ),
        ],
        "page": 1,
        "pages": 1,
        "rows_per_page": 20,
        "total": 11,
        "chrome": True,
        "display_user": True,
        "display_request": True,
        "package": "colin",
        "active_releases": False,
    }
)
