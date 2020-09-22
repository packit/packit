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

from contextlib import nullcontext as does_not_raise

import pytest
from flexmock import flexmock

import packit
from packit.actions import ActionName
from packit.exceptions import PackitException
from packit.local_project import LocalProject
from packit.upstream import Upstream
from tests.spellbook import get_test_config


@pytest.fixture
def package_config_mock():
    mock = flexmock(synced_files=None, upstream_package_name="test_package_name")
    mock.should_receive("current_version_command")
    return mock


@pytest.fixture
def git_project_mock():
    mock = flexmock(upstream_project_url="dummy_url")
    return mock


@pytest.fixture
def local_project_mock(git_project_mock):
    mock = flexmock(
        git_project=git_project_mock, working_dir="/mock_dir", ref="mock_ref"
    )
    return mock


@pytest.fixture
def upstream_mock(local_project_mock, package_config_mock):
    upstream = Upstream(
        config=get_test_config(),
        package_config=package_config_mock,
        local_project=LocalProject(working_dir="test"),
        # local_project=local_project_mock
    )
    flexmock(upstream)
    upstream.should_receive("local_project").and_return(local_project_mock)
    return upstream


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
    "package_name, version, orig_setup_line, new_setup_line",
    [
        pytest.param(
            "test_pkg_name",
            "0.42",
            ["%setup -q -n %{srcname}-%{version}"],
            ["%setup -q -n test_pkg_name-0.42"],
            id="test1",
        )
    ],
)
def test_fix_spec__setup_line(
    version, package_name, orig_setup_line, new_setup_line, upstream_mock, spec_mock
):
    flexmock(packit.upstream).should_receive("run_command").and_return("mocked")

    upstream_mock.package_config.upstream_package_name = package_name
    upstream_mock.should_receive("_fix_spec_source")
    upstream_mock.should_receive("specfile").and_return(
        spec_mock(setup_line=orig_setup_line)
    )

    upstream_mock.specfile.spec_content.should_receive("replace_section").with_args(
        "%prep", new_setup_line
    ).once().and_return(flexmock())

    upstream_mock.fix_spec("_archive", version, "_commit1234")


@pytest.mark.parametrize(
    "action_output, version, expected_result",
    [
        pytest.param(
            ("some_action_output", "1.0.1"), "_", "1.0.1", id="with_action_output"
        ),
        pytest.param(None, "1.0.2", "1.0.2", id="valid_version"),
        pytest.param(None, "1.0-3", "1.0.3", id="version_with_dash"),
    ],
)
def test_get_current_version(action_output, version, expected_result, upstream_mock):
    flexmock(packit.upstream.os).should_receive("listdir").and_return("mocked")
    upstream_mock.should_receive("get_output_from_action").and_return(action_output)
    upstream_mock.should_receive("command_handler.run_command").and_return("_mocked")
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
