# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import datetime

import pytest
from flexmock import flexmock

from packit.utils.koji_helper import KojiHelper


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_get_builds(error):
    nvrs = [f"test-1.{n}-1.fc37" for n in range(3)]

    def getPackageID(*_, **__):
        return 12345

    def listBuilds(*_, **__):
        if error:
            raise Exception
        return [{"nvr": nvr} for nvr in nvrs]

    session = flexmock(getPackageID=getPackageID, listBuilds=listBuilds)
    result = KojiHelper(session).get_nvrs("test", datetime.datetime(2022, 6, 1))
    if error:
        assert result == []
    else:
        assert result == nvrs


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_get_latest_nvr_in_tag(error):
    nvr = "test-1.0-1.fc37"

    def listTagged(*_, **__):
        if error:
            raise Exception
        return [{"nvr": nvr}]

    session = flexmock(listTagged=listTagged)
    result = KojiHelper(session).get_latest_nvr_in_tag("test", "f37-updates-candidate")
    if error:
        assert result is None
    else:
        assert result == nvr


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_get_build_tags(error):
    tags = ["f37-updates-testing"]

    def listTags(*_, **__):
        if error:
            raise Exception
        return [{"name": t} for t in tags]

    session = flexmock(listTags=listTags)
    result = KojiHelper(session).get_build_tags("test-1.0-1.fc37")
    if error:
        assert result == []
    else:
        assert result == tags


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_get_build_changelog(error):
    changelog = [
        (1655726400, "Nikola Forró <nforro@redhat.com> - 0.2-1.fc37", "- third entry"),
        (1652702400, "Nikola Forró <nforro@redhat.com> - 0.1-2.fc37", "- second entry"),
        (1648728000, "Nikola Forró <nforro@redhat.com> - 0.1-1.fc37", "- first entry"),
    ]

    def getRPMHeaders(*_, **__):
        if error:
            raise Exception
        result = list(zip(*changelog))
        return {
            "changelogtime": list(result[0]),
            "changelogname": list(result[1]),
            "changelogtext": list(result[2]),
        }

    session = flexmock(getRPMHeaders=getRPMHeaders)
    result = KojiHelper(session).get_build_changelog("test-0.2-1.fc37")
    if error:
        assert result == []
    else:
        assert result == changelog


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_get_builds_in_tag(error):
    builds = [
        {
            "package_name": "python-specfile",
            "name": "python3-specfile",
            "version": "0.28.0",
            "release": "1.fc39",
        },
    ]

    def listTagged(*_, **__):
        if error:
            raise Exception
        return builds

    session = flexmock(listTagged=listTagged)
    result = KojiHelper(session).get_builds_in_tag("f39-build-side-12345")
    if error:
        assert result == []
    else:
        assert result == builds


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_get_tag_info(error):
    info = {"name": "f39-build-side-12345", "id": 12345}

    def getBuildConfig(*_, **__):
        if error:
            raise Exception
        return info

    session = flexmock(getBuildConfig=getBuildConfig)
    result = KojiHelper(session).get_tag_info("f39-build-side-12345")
    if error:
        assert result is None
    else:
        assert result == info


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_create_sidetag(error):
    info = {"name": "f39-build-side-12345", "id": 12345}

    def createSideTag(*_, **__):
        if error:
            raise Exception
        return info

    session = flexmock(
        logged_in=True,
        getBuildTarget=lambda _: {"build_tag_name": "f39-build"},
        createSideTag=createSideTag,
    )
    result = KojiHelper(session).create_sidetag("f39")
    if error:
        assert result is None
    else:
        assert result == info


@pytest.mark.parametrize(
    "logged_in",
    [False, True],
)
def test_remove_sidetag(logged_in):
    session = flexmock(logged_in=logged_in)
    session.should_receive("gssapi_login").and_return().times(
        0 if logged_in else 1,
    ).mock()
    session.should_receive("removeSideTag").once()
    KojiHelper(session).remove_sidetag("f39-build-side-12345")


@pytest.mark.parametrize(
    "branch, target",
    [
        ("f39", "f39-candidate"),
        ("epel9", "epel9-candidate"),
        ("rawhide", "rawhide"),
        ("main", "rawhide"),
    ],
)
def test_get_build_target(branch, target):
    assert KojiHelper.get_build_target(branch) == target


@pytest.mark.parametrize(
    "since, formatted_changelog",
    [
        (
            1652702400,
            "* Mon Jun 20 2022 Nikola Forró <nforro@redhat.com> - 0.2-1\n"
            "- third entry\n",
        ),
        (
            1648728000,
            "* Mon Jun 20 2022 Nikola Forró <nforro@redhat.com> - 0.2-1\n"
            "- third entry\n"
            "\n"
            "* Mon May 16 2022 Nikola Forró <nforro@redhat.com> - 0.1-2\n"
            "- second entry\n",
        ),
        (
            0,
            "* Mon Jun 20 2022 Nikola Forró <nforro@redhat.com> - 0.2-1\n"
            "- third entry\n"
            "\n"
            "* Mon May 16 2022 Nikola Forró <nforro@redhat.com> - 0.1-2\n"
            "- second entry\n"
            "\n"
            "* Thu Mar 31 2022 Nikola Forró <nforro@redhat.com> - 0.1-1\n"
            "- first entry\n",
        ),
    ],
)
def test_format_changelog(since, formatted_changelog):
    changelog = [
        (1655726400, "Nikola Forró <nforro@redhat.com> - 0.2-1", "- third entry"),
        (1652702400, "Nikola Forró <nforro@redhat.com> - 0.1-2", "- second entry"),
        (1648728000, "Nikola Forró <nforro@redhat.com> - 0.1-1", "- first entry"),
    ]
    assert KojiHelper.format_changelog(changelog, since) == formatted_changelog


@pytest.mark.parametrize(
    "branch, tag",
    [
        ("f37", "f37-updates-candidate"),
        ("epel8", "epel8-testing-candidate"),
    ],
)
def test_get_candidate_tag(branch, tag):
    assert KojiHelper.get_candidate_tag(branch) == tag


@pytest.mark.parametrize(
    "tag, stable_tags",
    [
        ("f37-updates-candidate", ["f37-updates", "f37"]),
        ("f37-updates-testing", ["f37-updates", "f37"]),
        ("epel8-testing-candidate", ["epel8"]),
        ("epel8-testing", ["epel8"]),
        ("f37-updates", []),
        ("epel8", []),
        ("eln", []),
    ],
)
def test_get_stable_tags(tag, stable_tags):
    assert KojiHelper.get_stable_tags(tag) == stable_tags
