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

from contextlib import suppress as does_not_raise

import pytest
from flexmock import flexmock

import packit
from packit.actions import ActionName
from packit.exceptions import PackitException
from packit.upstream import Upstream


@pytest.fixture
def upstream_pr_mock():
    return flexmock(url="test_pr_url")


@pytest.fixture
def spec_mock():
    def spec_mock_factory(setup_line=""):
        spec_content_mock = flexmock()
        spec_content_mock.should_receive("section").and_return(setup_line)
        spec_content_mock.should_receive("replace_section").with_args(
            "%prep", setup_line
        ).and_return(flexmock())

        spec_mock = flexmock(
            spec_content=spec_content_mock,
            get_release_number=lambda: "1234567",
            set_spec_version=lambda **_: None,
            write_spec_content=flexmock(),
        )
        return spec_mock

    return spec_mock_factory


@pytest.fixture
def tar_mock():
    def tar_mock_factory(archive_items=[], is_tarfile=True):
        tarfile_mock = flexmock(packit.upstream.tarfile)
        tarinfo_mock_list = [
            flexmock(
                **{
                    "name": name,
                    "isdir": lambda v=isdir: v,
                    "isfile": lambda v=isdir: not isdir,
                }
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
    ups = Upstream(
        package_config=flexmock(
            actions={ActionName.create_archive: action_config}, synced_files=flexmock()
        ),
        config=flexmock(),
        local_project=flexmock(),
    )
    assert ups.get_commands_for_actions(action=ActionName.create_archive) == result


@pytest.mark.parametrize(
    "inner_archive_dir, orig_setup_line, new_setup_line",
    [
        pytest.param(
            "test_pkg_name-0.42",
            ["%setup -q -n %{srcname}-%{version}"],
            ["%setup -q -n test_pkg_name-0.42"],
            id="test1",
        )
    ],
)
def test_fix_spec__setup_line(
    inner_archive_dir, orig_setup_line, new_setup_line, upstream_mock, spec_mock
):
    flexmock(packit.upstream).should_receive("run_command").and_return("mocked")

    upstream_mock.should_receive("_fix_spec_source")
    upstream_mock.should_receive("get_archive_root_dir").and_return(inner_archive_dir)
    upstream_mock.should_receive("specfile").and_return(
        spec_mock(setup_line=orig_setup_line)
    )

    upstream_mock.specfile.spec_content.should_receive("replace_section").with_args(
        "%prep", new_setup_line
    ).once().and_return(flexmock())

    upstream_mock.fix_spec("_archive", "_version", "_commit1234")


@pytest.mark.parametrize(
    "action_output, current_version_command, version, expected_result",
    [
        pytest.param(
            ("some_action_output", "1.0.1"), None, "_", "1.0.1", id="with_action_output"
        ),
        pytest.param(None, "1.0.2", "_", "1.0.2", id="command_valid_version"),
        pytest.param(None, "1.0-3", "_", "1.0.3", id="command_version_with_dash"),
        pytest.param(None, None, "1.0.2", "1.0.2", id="tag_valid_version"),
        pytest.param(None, None, "1.0-3", "1.0.3", id="tag_version_with_dash"),
    ],
)
def test_get_current_version(
    action_output, current_version_command, version, expected_result, upstream_mock
):
    flexmock(packit.upstream.os).should_receive("listdir").and_return("mocked")
    upstream_mock.should_receive("get_output_from_action").and_return(action_output)
    # just to simulate if is configured or not
    upstream_mock.package_config.current_version_command = current_version_command
    upstream_mock.should_receive("command_handler.run_command").and_return(
        current_version_command
    )
    upstream_mock.should_receive("get_last_tag").and_return("_mocked")
    upstream_mock.should_receive("get_version_from_tag").and_return(version)
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
    tag, tag_template, expected_output, expectation, upstream_mock
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
        upstream_mock.should_receive("get_archive_root_dir_from_tar").and_return(
            return_value
        ).with_args("_archive").once()
        assert upstream_mock.get_archive_root_dir("_archive") == return_value
    elif archive_type == "unknown":
        upstream_mock.should_receive("get_archive_root_dir_from_template").and_return(
            return_value
        )
        tar_mock(is_tarfile=False)
        assert upstream_mock.get_archive_root_dir("_archive") == return_value


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
    assert upstream_mock.get_archive_root_dir_from_tar("_archive") == expected_result


@pytest.mark.parametrize(
    "template, expected_return_value",
    [
        pytest.param(
            "{upstream_pkg_name}-{version}", "test_package_name-1.0", id="default"
        ),
        pytest.param(
            "{version}-{upstream_pkg_name}", "1.0-test_package_name", id="custom"
        ),
        pytest.param("{unknown}-{version}", "{unknown}-1.0", id="unknown_tag"),
        pytest.param("static_string", "static_string", id="static_template"),
    ],
)
def test_get_archive_root_dir_from_template(
    template, expected_return_value, upstream_mock
):
    upstream_mock.should_receive("get_version").and_return("1.0")
    upstream_mock.package_config.archive_root_dir_template = template
    assert upstream_mock.get_archive_root_dir_from_template() == expected_return_value


@pytest.mark.parametrize(
    "version, tag_template, expected_output, expectation",
    [
        pytest.param(
            "1.0.0", "{version}", "1.0.0", does_not_raise(), id="valid_template"
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
    version, tag_template, expected_output, expectation, upstream_mock
):
    with expectation:
        upstream_mock.package_config.upstream_tag_template = tag_template
        assert upstream_mock.convert_version_to_tag(version) == expected_output
