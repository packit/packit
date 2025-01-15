# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import sys
from contextlib import suppress as does_not_raise

import pytest
from flexmock import flexmock

import packit
from packit.actions import ActionName
from packit.actions_handler import ActionsHandler
from packit.exceptions import PackitException
from packit.upstream import Archive, GitUpstream, SRPMBuilder


@pytest.fixture
def upstream_pr_mock():
    return flexmock(url="test_pr_url")


@pytest.fixture
def tar_mock():
    def tar_mock_factory(archive_items=None, is_tarfile=True):
        if archive_items is None:
            archive_items = []
        tarfile_mock = flexmock(packit.upstream.tarfile)
        tarinfo_mock_list = [
            flexmock(
                name=name,
                isdir=lambda v=isdir: v,
                isfile=lambda v=isdir: not v,
            )
            for name, isdir in archive_items
        ]
        tar_mock = flexmock(getmembers=lambda: tarinfo_mock_list)
        tarfile_mock.should_receive("open").and_return(tar_mock)
        tarfile_mock.should_receive("is_tarfile").and_return(is_tarfile)

    return tar_mock_factory


@pytest.mark.parametrize(
    "fork_username",
    [
        pytest.param("test_fork_username", id="fork_username_set"),
        pytest.param(None, id="fork_username_None"),
    ],
)
def test_create_pull(upstream_mock, upstream_pr_mock, fork_username):
    upstream_mock.local_project.git_project.should_receive("create_pr").with_args(
        title="test_title",
        body="test_description",
        source_branch="test_source",
        target_branch="test_target",
        fork_username=fork_username,
    ).and_return(upstream_pr_mock)
    upstream_mock.create_pull(
        pr_title="test_title",
        pr_description="test_description",
        source_branch="test_source",
        target_branch="test_target",
        fork_username=fork_username,
    )


@pytest.mark.parametrize(
    "action_config,result",
    [
        pytest.param("one cmd", [["one", "cmd"]], id="str_command"),
        pytest.param(["one cmd"], [["one", "cmd"]], id="list_command"),
        pytest.param([["one", "cmd"]], [["one", "cmd"]], id="list_in_list_command"),
        pytest.param(
            ["one cmd", "second cmd"],
            [["one", "cmd"], ["second", "cmd"]],
            id="two_str_commands_in_list",
        ),
        pytest.param(
            [["one", "cmd"], ["second", "cmd"]],
            [["one", "cmd"], ["second", "cmd"]],
            id="two_list_commands_in_list",
        ),
        pytest.param(
            [["one", "cmd"], "second cmd"],
            [["one", "cmd"], ["second", "cmd"]],
            id="one_str_and_one_list_command_in_list",
        ),
    ],
)
def test_get_commands_for_actions(action_config, result):
    ups = GitUpstream(
        package_config=flexmock(
            actions={ActionName.create_archive: action_config},
            files_to_sync=flexmock(),
        ),
        config=flexmock(),
        local_project=flexmock(),
    )
    ups._command_handler = flexmock()
    assert (
        ups.actions_handler.get_commands_for_actions(action=ActionName.create_archive)
        == result
    )


@pytest.mark.parametrize(
    "action_output, version, expected_result",
    [
        pytest.param(
            ("some_action_output", "1.0.1"),
            "_",
            "1.0.1",
            id="with_action_output",
        ),
        pytest.param(None, "1.0.2", "1.0.2", id="tag_valid_version"),
        pytest.param(None, "1.0-3", "1.0.3", id="tag_version_with_dash"),
    ],
)
def test_get_current_version(action_output, version, expected_result, upstream_mock):
    flexmock(packit.upstream.os).should_receive("listdir").and_return("mocked")
    flexmock(ActionsHandler).should_receive("get_output_from_action").and_return(
        action_output,
    )
    upstream_mock.should_receive("get_last_tag").and_return("_mocked")
    upstream_mock.should_receive("get_version_from_tag").and_return(version)
    upstream_mock.package_config.should_receive("get_package_names_as_env").and_return(
        {},
    )
    assert upstream_mock.get_current_version() == expected_result


@pytest.mark.parametrize(
    "tag, tag_template, expected_output, expectation",
    [
        pytest.param(
            "1.0.0",
            "{version}",
            "1.0.0",
            does_not_raise(),
            id="pure_version-valid_template",
        ),
        pytest.param(
            "test-1.0.0",
            "test-{version}",
            "1.0.0",
            does_not_raise(),
            id="valid_string-valid_template",
        ),
        pytest.param(
            "1.0.0",
            "tag-{random_field}",
            "1.0.0",
            pytest.raises(PackitException),
            id="missing_version_in_template",
        ),
        pytest.param(
            "some_name-1.0.0",
            "other_name-{version}",
            "1.0.0",
            pytest.raises(PackitException),
            id="no_match_found",
        ),
    ],
)
def test_get_version_from_tag(
    tag,
    tag_template,
    expected_output,
    expectation,
    upstream_mock,
):
    with expectation:
        upstream_mock.package_config.upstream_tag_template = tag_template
        assert upstream_mock.get_version_from_tag(tag) == expected_output


@pytest.mark.parametrize(
    "archive_type, return_value",
    [
        pytest.param("tar", "inner_archive_dir", id="tar_archive"),
        pytest.param("unknown", "dir_from_template", id="unknown_archive"),
    ],
)
def test_get_archive_root_dir(archive_type, return_value, upstream_mock, tar_mock):
    if archive_type == "tar":
        tar_mock(is_tarfile=True)
        flexmock(Archive).should_receive("get_archive_root_dir_from_tar").and_return(
            return_value,
        ).with_args("_archive").once()
        assert (
            Archive(upstream_mock, "").get_archive_root_dir("_archive") == return_value
        )
    elif archive_type == "unknown":
        flexmock(Archive).should_receive(
            "get_archive_root_dir_from_template",
        ).and_return(return_value)
        tar_mock(is_tarfile=False)
        assert (
            Archive(upstream_mock, "").get_archive_root_dir("_archive") == return_value
        )


@pytest.mark.parametrize(
    "archive_items, expected_result",
    [
        pytest.param(
            [("dir1", True), ("dir1/dir2", True), ("dir1/file1", False)],
            "dir1",
            id="valid_archive",
        ),
        pytest.param(
            [("dir1/dir2", True), ("dir1/file1", False)],
            "dir1",
            id="valid_archive_no_separate_top_level",
        ),
        pytest.param([], None, id="invalid_archive_empty"),
        pytest.param(
            [("dir1", True), ("dir2", True), ("dir1/file1", False)],
            None,
            id="invalid_two_dirs",
        ),
        pytest.param(
            [("dir1", True), ("dir1/dir2", True), ("file1", False)],
            "dir1",
            id="warning_file_in_root",
        ),
    ],
)
def test_get_tar_archive_dir(archive_items, expected_result, upstream_mock, tar_mock):
    tar_mock(archive_items=archive_items)
    assert (
        Archive(upstream_mock).get_archive_root_dir_from_tar("_archive")
        == expected_result
    )


@pytest.mark.parametrize(
    "template, expected_return_value",
    [
        pytest.param(
            "{upstream_pkg_name}-{version}",
            "test_package_name-1.0",
            id="default",
        ),
        pytest.param(
            "{version}-{upstream_pkg_name}",
            "1.0-test_package_name",
            id="custom",
        ),
        pytest.param("{unknown}-{version}", "{unknown}-1.0", id="unknown_tag"),
        pytest.param("static_string", "static_string", id="static_template"),
    ],
)
def test_get_archive_root_dir_from_template(
    template,
    expected_return_value,
    upstream_mock,
):
    upstream_mock.package_config.archive_root_dir_template = template
    assert (
        Archive(upstream_mock, "1.0").get_archive_root_dir_from_template()
        == expected_return_value
    )


@pytest.mark.parametrize(
    "version, tag_template, expected_output, expectation",
    [
        pytest.param(
            "1.0.0",
            "{version}",
            "1.0.0",
            does_not_raise(),
            id="valid_template",
        ),
        pytest.param(
            "1.0.0",
            "{rsion}",
            "1.0.0",
            pytest.raises(PackitException),
            id="invalid_template",
        ),
    ],
)
def test_convert_version_to_tag(
    version,
    tag_template,
    expected_output,
    expectation,
    upstream_mock,
):
    with expectation:
        upstream_mock.package_config.upstream_tag_template = tag_template
        assert upstream_mock.convert_version_to_tag(version) == expected_output


@pytest.mark.parametrize(
    "output, expected",
    (
        (
            "Wrote: packit-0.37.1.dev13+gd57da48.rpm.regex.broken.13.gd57da48.fc35.noarch.rpm",
            [
                "packit-0.37.1.dev13+gd57da48.rpm.regex.broken.13.gd57da48.fc35.noarch.rpm",
            ],
        ),
        (
            "Processing files: python3-packit-0.37.1.dev14+g860168a.d20211004-1."
            "20211004105435567001.rpm.regex.broken.14.g860168a.fc35.noarch\n"
            "\nAnother false positive: random_rpm_named_with_space .rpm"
            "Wrote: packit-0.37.1.dev13+gd57da48.rpm.regex.broken.13.gd57da48.fc35.noarch.rpm",
            [
                "packit-0.37.1.dev13+gd57da48.rpm.regex.broken.13.gd57da48.fc35.noarch.rpm",
            ],
        ),
        (
            "Wrote: packit-0.37.1.dev13+gd57da48.rpm.regex.broken.13.gd57da48.fc35.noarch.rpm"
            "\n\n\nWrote: packit-0.38.0.rpma.fc35.noarch.rpm\n"
            "Wrote: packit-0.38.0.rpm_hmm.fc35.noarch.rpm\n",
            [
                "packit-0.37.1.dev13+gd57da48.rpm.regex.broken.13.gd57da48.fc35.noarch.rpm",
                "packit-0.38.0.rpma.fc35.noarch.rpm",
                "packit-0.38.0.rpm_hmm.fc35.noarch.rpm",
            ],
        ),
    ),
)
def test_get_rpms_from_rpmbuild_output(output, expected):
    assert GitUpstream._get_rpms_from_rpmbuild_output(output) == expected


@pytest.mark.parametrize(
    ("archive", "version", "release_suffix", "expanded_release_suffix"),
    [
        ("archive.tar.gz", "1.0.0", "123", "123"),
        # not allowed outside of tests, but the SHA is hardcoded for local project
        ("ravl.tar.bz2", "1.2.3", "{PACKIT_PROJECT_COMMIT}", "_"),
        ("one_piece.tar.gz", "1.0.2", "{PACKIT_PROJECT_BRANCH}", "mock_ref"),
        (
            "something.zip",
            "1.0.2",
            "{PACKIT_PROJECT_BRANCH}.{PACKIT_PROJECT_VERSION}",
            "mock_ref.1.0.2",
        ),
    ],
)
def test_release_suffix(
    upstream_mock,
    archive,
    version,
    release_suffix,
    expanded_release_suffix,
):
    flexmock(upstream_mock).should_receive("get_current_version").and_return(version)
    flexmock(upstream_mock).should_receive("get_spec_release").and_return(
        expanded_release_suffix,
    )
    upstream_mock.package_config.should_receive("get_package_names_as_env").and_return(
        {},
    )
    flexmock(upstream_mock).should_receive("specfile").and_return(
        flexmock(expanded_release=expanded_release_suffix)
        .should_receive("reload")
        .and_return(None)
        .mock(),
    )

    flexmock(upstream_mock).should_receive("fix_spec").with_args(
        archive=archive,
        version=version,
        commit="_",
        update_release=True,
        release=expanded_release_suffix,
    )

    SRPMBuilder(upstream_mock)._fix_specfile_to_use_local_archive(
        archive=archive,
        update_release=True,
        release_suffix=release_suffix,
    )


@pytest.mark.parametrize(
    "rpmbuild_output",
    (
        pytest.param(
            "setting SOURCE_DATE_EPOCH=1668038400"
            "Wrote: ./koji-c-1.1.0-1.20221110110837054647.pr257.1.g8477d03.fc35.src.rpm"
            "RPM build warnings:"
            "    extra tokens at the end of %endif directive in line 66:  %endif # with_python3",
            id="output_after",
        ),
        pytest.param(
            "setting SOURCE_DATE_EPOCH=1668038400"
            "Wrote: ./koji-c-1.1.0-1.20221110110837054647.pr257.1.g8477d03.fc35.src.rpm",
            id="common_output",
        ),
    ),
)
def test_get_srpm_from_rpmbuild_output(upstream_mock, rpmbuild_output):
    srpm = "./koji-c-1.1.0-1.20221110110837054647.pr257.1.g8477d03.fc35.src.rpm"
    assert srpm == SRPMBuilder(upstream_mock)._get_srpm_from_rpmbuild_output(
        rpmbuild_output,
    )


@pytest.mark.parametrize(
    "update_release,release_suffix,expected_release",
    (
        # current_git_tag_version="4.5"
        # original_release_number_from_spec = "2"
        pytest.param(
            True,
            "",
            # update-release from command line wins over release_suffix on packit.yaml
            "2.1234.mock_ref.",
            id="Bump release, release_suffix is empty",
        ),
        pytest.param(
            True,
            None,
            "2.1234.mock_ref.",
            id="Bump release, release_suffix is None",
        ),
        pytest.param(True, "7", "2.7", id="Bump release, release_suffix value is 7"),
        pytest.param(
            True,
            "{PACKIT_RPMSPEC_RELEASE}",
            "2.1234.mock_ref.",
            id="Bump release, release_suffix value is a macro {PACKIT_RPMSPEC_RELEASE}",
        ),
        pytest.param(
            False,
            "",
            "2.1234.mock_ref.",
            id="Do not modify release, release_suffix is empty",
        ),
        pytest.param(
            False,
            None,
            "2.1234.mock_ref.",
            id="Do not modify release, release_suffix is None",
        ),
        pytest.param(
            False,
            "7",
            "2.7",
            id="Do not modify release, release_suffix value is 7",
        ),
        pytest.param(
            False,
            "{PACKIT_RPMSPEC_RELEASE}",
            "2.1234.mock_ref.",
            id="Do not modify release, release_suffix value is a macro {PACKIT_RPMSPEC_RELEASE}",
        ),
    ),
)
def test_get_spec_release(
    upstream_mock,
    update_release,
    release_suffix,
    expected_release,
):
    archive = "an_archive_name"
    current_git_tag_version = "4.5"
    original_release_number_from_spec = "2"
    flexmock(upstream_mock).should_receive("get_current_version").and_return(
        current_git_tag_version,
    )
    upstream_mock.package_config.should_receive("get_package_names_as_env").and_return(
        {},
    )

    flexmock(sys.modules["packit.upstream"]).should_receive("datetime").and_return(
        flexmock(datetime=flexmock(now=flexmock(strftime=lambda f: "1234"))),
    )

    flexmock(upstream_mock).should_receive("fix_spec").with_args(
        archive=archive,
        version=current_git_tag_version,
        commit="_",
        update_release=update_release,
        release=expected_release,
    )
    upstream_mock._specfile = flexmock(
        expanded_release=original_release_number_from_spec,
    )
    upstream_mock._specfile.should_receive("reload").once()

    flexmock(sys.modules["packit.upstream"]).should_receive("run_command").and_return(
        flexmock(stdout=current_git_tag_version),
    )

    SRPMBuilder(upstream_mock)._fix_specfile_to_use_local_archive(
        archive=archive,
        update_release=update_release,
        release_suffix=release_suffix,
    )


@pytest.mark.parametrize(
    "update_release,had_disttag,release_suffix,expected_release_suffix",
    (
        # current_git_tag_version="4.5"
        # original_release_number_from_spec = "2"
        # original_dist_from_spec = "%{?dist}" if had_disttag else ""
        pytest.param(
            True,
            False,
            "",
            # update-release from command line wins over release_suffix on packit.yaml
            "2.1234.mock_ref.%{?dist}",
            id="Bump release, release_suffix is empty",
        ),
        pytest.param(
            True,
            False,
            None,
            "2.1234.mock_ref.%{?dist}",
            id="Bump release, release_suffix is None",
        ),
        pytest.param(
            True,
            False,
            "7",
            "2.7%{?dist}",
            id="Bump release, release_suffix value is 7",
        ),
        pytest.param(
            True,
            False,
            "{PACKIT_RPMSPEC_RELEASE}",
            "2.1234.mock_ref.%{?dist}",
            id="Bump release, release_suffix value is a macro {PACKIT_RPMSPEC_RELEASE}",
        ),
        pytest.param(
            True,
            True,
            "",
            "2.1234.mock_ref.",
            id="Bump release, release_suffix is empty, make sure %{?dist} tag is not duplicated",
        ),
        pytest.param(
            True,
            True,
            "{PACKIT_RPMSPEC_RELEASE}",
            "2.1234.mock_ref.",
            id="Bump release, release_suffix is a macro, make sure %{?dist} tag is not duplicated",
        ),
        pytest.param(
            True,
            False,
            "{PACKIT_RPMSPEC_RELEASE}%{{?dist}}",
            "2.1234.mock_ref.%{?dist}",
            id="Bump release, make sure %{?dist} tag is not duplicated",
        ),
        pytest.param(
            False,
            False,
            "",
            "2.1234.mock_ref.",
            id="Do not modify release, release_suffix is empty",
        ),
        pytest.param(
            False,
            False,
            None,
            "2.1234.mock_ref.",
            id="Do not modify release, release_suffix is None",
        ),
        pytest.param(
            False,
            False,
            "7",
            "2.7",
            id="Do not modify release, release_suffix value is 7",
        ),
        pytest.param(
            False,
            False,
            "{PACKIT_RPMSPEC_RELEASE}",
            "2.1234.mock_ref.",
            id="Do not modify release, release_suffix value is a macro {PACKIT_RPMSPEC_RELEASE}",
        ),
    ),
)
def test_fix_spec(
    upstream_mock,
    update_release,
    had_disttag,
    release_suffix,
    expected_release_suffix,
):
    upstream_mock.package_config.upstream_tag_include = None
    upstream_mock.package_config.upstream_tag_exclude = None
    upstream_mock.package_config.should_receive("get_package_names_as_env").and_return(
        {},
    )
    archive = "an_archive_name"
    current_git_tag_version = "4.5"
    original_release_number_from_spec = "2"
    flexmock(upstream_mock).should_receive("get_current_version").and_return(
        current_git_tag_version,
    )

    flexmock(sys.modules["packit.upstream"]).should_receive("datetime").and_return(
        flexmock(datetime=flexmock(now=flexmock(strftime=lambda f: "1234"))),
    )

    flexmock(upstream_mock).should_receive("_fix_spec_source").with_args(
        archive=archive,
    )
    flexmock(upstream_mock).should_receive("_fix_spec_prep").with_args(archive=archive)

    disttag = "%{?dist}" if had_disttag else ""
    upstream_mock._specfile = flexmock(
        expanded_release=original_release_number_from_spec,
        raw_release=f"{original_release_number_from_spec}{disttag}",
    )
    upstream_mock._specfile.should_receive("reload").once()

    if update_release:
        upstream_mock._specfile.should_receive("add_changelog_entry")

    flexmock(sys.modules["packit.upstream"]).should_receive("run_command").and_return(
        flexmock(stdout=current_git_tag_version),
    )

    SRPMBuilder(upstream_mock)._fix_specfile_to_use_local_archive(
        archive=archive,
        update_release=update_release,
        release_suffix=release_suffix,
    )

    assert upstream_mock._specfile.version == current_git_tag_version

    if update_release:
        assert upstream_mock._specfile.release == expected_release_suffix
