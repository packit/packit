# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import datetime

import pytest
from flexmock import flexmock
from koji import ActionNotAllowed, AuthError, ClientSession

from packit.utils.koji_helper import KojiHelper


def koji_session_virtual_method(requires_authentication=False, invalid_session=False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if getattr(wrapper, "first_call", True):
                wrapper.first_call = False
                if requires_authentication:
                    raise ActionNotAllowed
                if invalid_session:
                    raise AuthError
            wrapper.first_call = False
            return func(*args, **kwargs)

        wrapper._VirtualMethod__name = func.__name__
        return wrapper

    return decorator


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_get_builds(error):
    nvrs = [f"test-1.{n}-1.fc37" for n in range(3)]

    @koji_session_virtual_method()
    def getPackageID(*_, **__):
        return 12345

    @koji_session_virtual_method()
    def listBuilds(*_, **__):
        if error:
            raise Exception
        return [{"nvr": nvr} for nvr in nvrs]

    flexmock(ClientSession).new_instances(
        flexmock(getPackageID=getPackageID, listBuilds=listBuilds),
    )
    result = KojiHelper().get_nvrs("test", datetime.datetime(2022, 6, 1))
    if error:
        assert result == []
    else:
        assert result == nvrs


@pytest.mark.parametrize(
    "include_candidate, nvr",
    [
        (False, "test-1.0-2.fc40"),
        (True, "test-2.0-1.fc40"),
    ],
)
def test_get_latest_stable_nvr(include_candidate, nvr):
    candidate_tags = {"f40": "f40-updates-candidate"}
    stable_tags = {"f40-updates-candidate": ["f40-updates", "f40"]}
    builds = {
        "f40-updates-candidate": {"nvr": "test-2.0-1.fc40"},
        "f40-updates": {"nvr": "test-1.0-2.fc40"},
        "f40": {"nvr": "test-1.0-1.fc40"},
    }

    flexmock(ClientSession).new_instances(flexmock())
    koji_helper = KojiHelper()
    flexmock(
        koji_helper,
        get_candidate_tag=lambda b: candidate_tags[b],
        get_stable_tags=lambda t: stable_tags[t],
        get_latest_build_in_tag=lambda _, t: builds[t],
    )
    assert koji_helper.get_latest_stable_nvr("test", "f40", include_candidate) == nvr


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_get_latest_nvr_in_tag(error):
    nvr = "test-1.0-1.fc37"

    @koji_session_virtual_method()
    def listTagged(*_, **__):
        if error:
            raise Exception
        return [{"nvr": nvr}]

    flexmock(ClientSession).new_instances(flexmock(listTagged=listTagged))
    result = KojiHelper().get_latest_nvr_in_tag("test", "f37-updates-candidate")
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

    @koji_session_virtual_method()
    def listTags(*_, **__):
        if error:
            raise Exception
        return [{"name": t} for t in tags]

    flexmock(ClientSession).new_instances(flexmock(listTags=listTags))
    result = KojiHelper().get_build_tags("test-1.0-1.fc37")
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

    @koji_session_virtual_method()
    def getRPMHeaders(*_, **__):
        if error:
            raise Exception
        result = list(zip(*changelog))
        return {
            "changelogtime": list(result[0]),
            "changelogname": list(result[1]),
            "changelogtext": list(result[2]),
        }

    flexmock(ClientSession).new_instances(flexmock(getRPMHeaders=getRPMHeaders))
    result = KojiHelper().get_build_changelog("test-0.2-1.fc37")
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

    @koji_session_virtual_method()
    def listTagged(*_, **__):
        if error:
            raise Exception
        return builds

    flexmock(ClientSession).new_instances(flexmock(listTagged=listTagged))
    result = KojiHelper().get_builds_in_tag("f39-build-side-12345")
    if error:
        assert result == []
    else:
        assert result == builds


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_get_build_info(error):
    info = {"id": 123456, "name": "test", "nvr": "test-1.0-1.fc39"}

    @koji_session_virtual_method()
    def getBuild(*_, **__):
        if error:
            raise Exception
        return info

    flexmock(ClientSession).new_instances(flexmock(getBuild=getBuild))
    for build in [123456, "test-1.0-1.fc39"]:
        result = KojiHelper().get_build_info(build)
        if error:
            assert result is None
        else:
            assert result == info


@pytest.mark.parametrize(
    "error, auth_error",
    [(False, False), (True, False), (False, True)],
)
def test_get_tag_info(error, auth_error):
    info = {"name": "f39-build-side-12345", "id": 12345}

    @koji_session_virtual_method(invalid_session=auth_error)
    def getBuildConfig(*_, **__):
        if error:
            raise Exception
        return info

    flexmock(ClientSession).new_instances(flexmock(getBuildConfig=getBuildConfig))
    result = KojiHelper().get_tag_info("f39-build-side-12345")
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

    @koji_session_virtual_method(requires_authentication=True)
    def createSideTag(*_, **__):
        if error:
            raise Exception
        return info

    session = flexmock(createSideTag=createSideTag)
    session.should_receive("gssapi_login").once()
    flexmock(ClientSession).new_instances(session)
    koji_helper = KojiHelper()
    flexmock(koji_helper, get_build_target=lambda _: {"build_tag_name": "f39-build"})
    result = koji_helper.create_sidetag("f39")
    if error:
        assert result is None
    else:
        assert result == info


@pytest.mark.parametrize(
    "logged_in",
    [False, True],
)
def test_remove_sidetag(logged_in):
    @koji_session_virtual_method(requires_authentication=not logged_in)
    def removeSideTag(*_, **__):
        pass

    session = flexmock(removeSideTag=removeSideTag)
    session.should_receive("gssapi_login").times(
        0 if logged_in else 1,
    )
    flexmock(ClientSession).new_instances(session)
    KojiHelper().remove_sidetag("f39-build-side-12345")


@pytest.mark.parametrize(
    "logged_in",
    [False, True],
)
def test_tag_build(logged_in):
    @koji_session_virtual_method(requires_authentication=not logged_in)
    def tagBuild(*_, **__):
        return 12345

    session = flexmock(tagBuild=tagBuild)
    session.should_receive("gssapi_login").times(
        0 if logged_in else 1,
    )
    flexmock(ClientSession).new_instances(session)
    KojiHelper().tag_build("test-1.0-1.fc39", "f39-build-side-12345")


@pytest.mark.parametrize(
    "logged_in",
    [False, True],
)
def test_untag_build(logged_in):
    @koji_session_virtual_method(requires_authentication=not logged_in)
    def untagBuild(*_, **__):
        pass

    session = flexmock(untagBuild=untagBuild)
    session.should_receive("gssapi_login").times(
        0 if logged_in else 1,
    )
    flexmock(ClientSession).new_instances(session)
    KojiHelper().untag_build("test-1.0-1.fc39", "f39-build-side-12345")


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_get_build_target(error):
    target = {
        "id": 123456,
        "build_tag_name": "f39-build",
        "dest_tag_name": "f39-updates-candidate",
    }

    @koji_session_virtual_method()
    def getBuildTarget(*_, **__):
        if error:
            raise Exception
        return target

    flexmock(ClientSession).new_instances(flexmock(getBuildTarget=getBuildTarget))
    result = KojiHelper().get_build_target("f39")
    if error:
        assert result is None
    else:
        assert result == target


@pytest.mark.parametrize(
    "target, branch",
    [
        ("f41-candidate", "f41"),
        ("f43-candidate", "rawhide"),
        ("epel9", "epel9"),
        ("epel10.1-candidate", "epel10"),
    ],
)
def test_get_branch_from_target_name(target, branch):
    targets = {
        "f41-candidate": {
            "build_tag_name": "f41-build",
            "dest_tag_name": "f41-updates-candidate",
        },
        "f43-candidate": {
            "build_tag_name": "f43-build",
            "dest_tag_name": "f43-updates-candidate",
        },
        "epel9": {
            "build_tag_name": "epel9-build",
            "dest_tag_name": "epel9-testing-candidate",
        },
        "epel10.1-candidate": {
            "build_tag_name": "epel10.1-build",
            "dest_tag_name": "epel10.1-testing-candidate",
        },
    }

    candidate_tags = {
        "rawhide": "f43-updates-candidate",
        "epel10": "epel10.1-testing-candidate",
    }

    stable_tags = {
        "f41-updates-candidate": ["f41-updates", "f41"],
        "epel9-testing-candidate": ["epel9"],
    }

    @koji_session_virtual_method()
    def getBuildTarget(target_name, *_, **__):
        return targets[target_name]

    def get_candidate_tag(branch, *_, **__):
        return candidate_tags[branch]

    def get_stable_tags(tag, *_, **__):
        return stable_tags[tag]

    flexmock(ClientSession).new_instances(flexmock(getBuildTarget=getBuildTarget))
    koji_helper = KojiHelper()
    flexmock(
        koji_helper,
        get_candidate_tag=get_candidate_tag,
        get_stable_tags=get_stable_tags,
    )
    assert koji_helper.get_branch_from_target_name(target) == branch


@pytest.mark.parametrize(
    "branch, tag",
    [
        ("f39", "f39-updates-candidate"),
        ("epel9", "epel9-testing-candidate"),
        ("eln", "eln-updates-candidate"),
        ("rawhide", "f41-updates-candidate"),
    ],
)
def test_get_candidate_tag(branch, tag):
    targets = {
        "f39": {
            "build_tag_name": "f39-build",
            "dest_tag_name": "f39-updates-candidate",
        },
        "epel9": {
            "build_tag_name": "epel9-build",
            "dest_tag_name": "epel9-testing-candidate",
        },
        "eln": {
            "build_tag_name": "eln-build",
            "dest_tag_name": "eln-updates-candidate",
        },
        "rawhide": {
            "build_tag_name": "f41-build",
            "dest_tag_name": "f41-updates-candidate",
        },
    }

    def get_build_target(branch, *_, **__):
        return targets[branch]

    flexmock(ClientSession).new_instances(flexmock())
    koji_helper = KojiHelper()
    flexmock(koji_helper, get_build_target=get_build_target)
    assert koji_helper.get_candidate_tag(branch) == tag


@pytest.mark.parametrize(
    "tag, stable_tags",
    [
        ("f37-updates-candidate", ["f37-updates", "f37"]),
        ("f37-updates-testing", ["f37-updates", "f37"]),
        ("epel8-testing-candidate", ["epel8"]),
        ("epel8-testing", ["epel8"]),
        ("f37-updates", ["f37-updates", "f37"]),
        ("epel8", ["epel8"]),
        ("eln", ["eln", "f41"]),
        ("f40-build-side-12345", ["f40-updates", "f40"]),
    ],
)
def test_get_stable_tags(tag, stable_tags):
    ancestors = {
        "f37-updates-candidate": [{"name": "f37-updates"}, {"name": "f37"}],
        "f37-updates-testing": [{"name": "f37-updates"}, {"name": "f37"}],
        "epel8-testing-candidate": [{"name": "epel8"}],
        "epel8-testing": [{"name": "epel8"}],
        "f37-updates": [{"name": "f37"}],
        "epel8": [],
        "eln": [{"name": "f41"}],
        "f40-build-side-12345": [
            {"name": "f40-build"},
            {"name": "f40-override"},
            {"name": "f40-updates"},
            {"name": "f40"},
        ],
    }

    @koji_session_virtual_method()
    def getFullInheritance(tag, *_, **__):
        return ancestors[tag]

    flexmock(ClientSession).new_instances(
        flexmock(getFullInheritance=getFullInheritance),
    )
    assert KojiHelper().get_stable_tags(tag) == stable_tags


@pytest.mark.parametrize(
    "branch, target",
    [
        ("f39", "f39-candidate"),
        ("epel9", "epel9-candidate"),
        ("eln", "eln-candidate"),
        ("rawhide", "rawhide"),
        ("main", "rawhide"),
    ],
)
def test_get_build_target_name(branch, target):
    assert KojiHelper.get_build_target_name(branch) == target


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
