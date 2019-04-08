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

import os
from pathlib import Path

import pytest
from flexmock import flexmock
from jsonschema.exceptions import ValidationError

from packit.actions import ActionName
from tests.spellbook import TESTS_DIR
from ogr.abstract import GitProject, GitService
from packit.config import (
    JobConfig,
    PackageConfig,
    TriggerType,
    SyncFilesConfig,
    SyncFilesItem,
    get_packit_config_from_repo,
    Config,
)

from packit.sync import get_wildcard_resolved_sync_files
from tests.utils import cwd


def test_job_config_equal():
    assert JobConfig(
        trigger=TriggerType.release, release_to=["f28"], metadata={}
    ) == JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})


def test_job_config_not_equal():
    assert not JobConfig(
        trigger=TriggerType.release, release_to=["f28"], metadata={}
    ) == JobConfig(trigger=TriggerType.release, release_to=["f29"], metadata={})


@pytest.mark.parametrize(
    "raw,is_valid",
    [
        ({}, False),
        ({"trigger": "release"}, False),
        ({"release_to": ["f28"]}, False),
        ({"trigger": "release", "release_to": ["f28"]}, True),
        ({"trigger": "pull_request", "release_to": ["f28"]}, True),
        ({"trigger": "git_tag", "release_to": ["f28"]}, True),
        ({"trigger": "release", "release_to": ["f28", "rawhide", "f29"]}, True),
        (
            {
                "trigger": "release",
                "release_to": ["f28"],
                "some": "other",
                "metadata": "info",
            },
            True,
        ),
    ],
)
def test_job_config_validate(raw, is_valid):
    assert JobConfig.is_dict_valid(raw) == is_valid


@pytest.mark.parametrize("raw", [{}, {"trigger": "release"}, {"release_to": ["f28"]}])
def test_job_config_parse_error(raw):
    with pytest.raises(Exception):
        JobConfig.get_from_dict(raw_dict=raw)


@pytest.mark.parametrize(
    "raw,expected_config",
    [
        (
            {"trigger": "release", "release_to": ["f28"]},
            JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={}),
        ),
        (
            {"trigger": "pull_request", "release_to": ["f28"]},
            JobConfig(
                trigger=TriggerType.pull_request, release_to=["f28"], metadata={}
            ),
        ),
        (
            {"trigger": "git_tag", "release_to": ["f28"]},
            JobConfig(trigger=TriggerType.git_tag, release_to=["f28"], metadata={}),
        ),
        (
            {"trigger": "release", "release_to": ["f28", "rawhide", "f29"]},
            JobConfig(
                trigger=TriggerType.release,
                release_to=["f28", "rawhide", "f29"],
                metadata={},
            ),
        ),
        (
            {
                "trigger": "release",
                "release_to": ["f28"],
                "some": "other",
                "metadata": "info",
            },
            JobConfig(
                trigger=TriggerType.release,
                release_to=["f28"],
                metadata={"some": "other", "metadata": "info"},
            ),
        ),
    ],
)
def test_job_config_parse(raw, expected_config):
    job_config = JobConfig.get_from_dict(raw_dict=raw)
    assert job_config == expected_config


def test_package_config_equal():
    assert PackageConfig(
        specfile_path="fedora/package.spec",
        synced_files=SyncFilesConfig(
            files_to_sync=[SyncFilesItem(src="packit.yaml", dest="packit.yaml")]
        ),
        jobs=[JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})],
    ) == PackageConfig(
        specfile_path="fedora/package.spec",
        synced_files=SyncFilesConfig(
            files_to_sync=[SyncFilesItem(src="packit.yaml", dest="packit.yaml")]
        ),
        jobs=[JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})],
    )


@pytest.mark.parametrize(
    "not_equal_package_config",
    [
        PackageConfig(
            specfile_path="fedora/other-package.spec",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="a", dest="a"),
                    SyncFilesItem(src="b", dest="b"),
                ]
            ),
            jobs=[
                JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})
            ],
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="c", dest="c")]
            ),
            jobs=[
                JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})
            ],
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="a", dest="a"),
                    SyncFilesItem(src="b", dest="b"),
                ]
            ),
            jobs=[
                JobConfig(
                    trigger=TriggerType.pull_request, release_to=["f28"], metadata={}
                )
            ],
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="c", dest="c"),
                    SyncFilesItem(src="d", dest="d"),
                ]
            ),
            jobs=[
                JobConfig(trigger=TriggerType.release, release_to=["f29"], metadata={})
            ],
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="c", dest="c"),
                    SyncFilesItem(src="d", dest="d"),
                ]
            ),
            jobs=[
                JobConfig(
                    trigger=TriggerType.release, release_to=["f28"], metadata={"a": "b"}
                )
            ],
        ),
    ],
)
def test_package_config_not_equal(not_equal_package_config):
    assert (
        not PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="c", dest="c"),
                    SyncFilesItem(src="d", dest="d"),
                ]
            ),
            jobs=[
                JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})
            ],
        )
        == not_equal_package_config
    )


@pytest.mark.parametrize(
    "raw,is_valid",
    [
        ({}, False),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": "fedora/foobar.spec",
            },
            False,
        ),
        ({"jobs": [{"trigger": "release", "release_to": ["f28"]}]}, False),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/foobar.spec"],
                "jobs": [{"trigger": "release", "release_to": ["f28"]}],
            },
            True,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/foobar.spec", "somefile", "somedirectory"],
                "jobs": [
                    {"trigger": "release", "release_to": ["f28"]},
                    {"trigger": "pull_request", "release_to": ["f29", "f30", "master"]},
                ],
            },
            True,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/foobar.spec"],
                "jobs": [
                    {"trigger": "release", "release_to": ["f28"]},
                    {"trigger": "pull_request", "release_to": ["f29", "f30", "master"]},
                    {"trigger": "git_tag", "release_to": ["f29", "f30", "master"]},
                ],
            },
            True,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/foobar.spec"],
                "actions": {
                    "pre-sync": "some/pre-sync/command --option",
                    "get-current-version": "get-me-version",
                },
                "jobs": [
                    {"trigger": "release", "release_to": ["f28"]},
                    {"trigger": "pull_request", "release_to": ["f29", "f30", "master"]},
                    {"trigger": "git_tag", "release_to": ["f29", "f30", "master"]},
                ],
            },
            True,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/foobar.spec"],
                "actions": {
                    "pre-sync": "some/pre-sync/command --option",
                    "unknown-action": "nothing",
                },
                "jobs": [
                    {"trigger": "release", "release_to": ["f28"]},
                    {"trigger": "pull_request", "release_to": ["f29", "f30", "master"]},
                    {"trigger": "git_tag", "release_to": ["f29", "f30", "master"]},
                ],
            },
            False,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "actions": ["actions" "has", "to", "be", "key", "value"],
                "jobs": [
                    {"trigger": "release", "release_to": ["f28"]},
                    {"trigger": "pull_request", "release_to": ["f29", "f30", "master"]},
                    {"trigger": "git_tag", "release_to": ["f29", "f30", "master"]},
                ],
            },
            False,
        ),
    ],
)
def test_package_config_validate(raw, is_valid):
    if not is_valid:
        with pytest.raises(ValidationError):
            PackageConfig.validate_dict(raw)
    else:
        PackageConfig.validate_dict(raw)


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"something": "different"},
        {"synced_files": ["fedora/package.spec", "somefile"]},
        {"jobs": [{"trigger": "release", "release_to": ["f28"]}]},
    ],
)
def test_package_config_parse_error(raw):
    with pytest.raises(Exception):
        PackageConfig.get_from_dict(raw_dict=raw)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/package.spec"],
                "jobs": [{"trigger": "release", "release_to": ["f28"]}],
            },
            PackageConfig(
                specfile_path=str(Path.cwd().joinpath("fedora/package.spec")),
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        )
                    ]
                ),
                jobs=[
                    JobConfig(
                        trigger=TriggerType.release, release_to=["f28"], metadata={}
                    )
                ],
            ),
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": [
                    "fedora/package.spec",
                    "somefile",
                    "other",
                    "directory/files",
                ],
                "jobs": [{"trigger": "release", "release_to": ["f28"]}],
            },
            PackageConfig(
                specfile_path=str(Path.cwd().joinpath("fedora/package.spec")),
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        ),
                        SyncFilesItem(src="somefile", dest="somefile"),
                        SyncFilesItem(src="other", dest="other"),
                        SyncFilesItem(src="directory/files", dest="directory/files"),
                    ]
                ),
                jobs=[
                    JobConfig(
                        trigger=TriggerType.release, release_to=["f28"], metadata={}
                    )
                ],
            ),
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/package.spec"],
                "jobs": [{"trigger": "release", "release_to": ["f28"]}],
            },
            PackageConfig(
                specfile_path=str(Path.cwd().joinpath("fedora/package.spec")),
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        )
                    ]
                ),
                jobs=[
                    JobConfig(
                        trigger=TriggerType.release, release_to=["f28"], metadata={}
                    )
                ],
            ),
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/package.spec", "somefile"],
                "jobs": [{"trigger": "release", "release_to": ["f28"]}],
                "something": "stupid",
            },
            PackageConfig(
                specfile_path=str(Path.cwd().joinpath("fedora/package.spec")),
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        ),
                        SyncFilesItem(src="somefile", dest="somefile"),
                    ]
                ),
                jobs=[
                    JobConfig(
                        trigger=TriggerType.release, release_to=["f28"], metadata={}
                    )
                ],
            ),
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/package.spec"],
                "jobs": [{"trigger": "release", "release_to": ["f28"]}],
                "something": "stupid",
                "upstream_project_url": "https://github.com/asd/qwe",
                "upstream_project_name": "qwe",
                "dist_git_base_url": "https://something.wicked",
            },
            PackageConfig(
                specfile_path=str(Path.cwd().joinpath("fedora/package.spec")),
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        )
                    ]
                ),
                jobs=[
                    JobConfig(
                        trigger=TriggerType.release, release_to=["f28"], metadata={}
                    )
                ],
                upstream_project_url="https://github.com/asd/qwe",
                upstream_project_name="qwe",
                dist_git_base_url="https://something.wicked",
            ),
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "actions": {
                    "pre-sync": "some/pre-sync/command --option",
                    "get-current-version": "get-me-version",
                },
                "jobs": [],
                "something": "stupid",
                "upstream_project_url": "https://github.com/asd/qwe",
                "upstream_project_name": "qwe",
                "dist_git_base_url": "https://something.wicked",
            },
            PackageConfig(
                specfile_path=str(Path.cwd().joinpath("fedora/package.spec")),
                actions={
                    ActionName.pre_sync: "some/pre-sync/command --option",
                    ActionName.get_current_version: "get-me-version",
                },
                jobs=[],
                upstream_project_url="https://github.com/asd/qwe",
                upstream_project_name="qwe",
                dist_git_base_url="https://something.wicked",
            ),
        ),
    ],
)
def test_package_config_parse(raw, expected):
    package_config = PackageConfig.get_from_dict(raw_dict=raw)
    assert package_config
    assert package_config == expected


def test_dist_git_package_url():
    di = {
        "dist_git_base_url": "https://packit.dev/",
        "downstream_package_name": "packit",
        "dist_git_namespace": "awesome",
        "synced_files": ["fedora/foobar.spec"],
        "specfile_path": "fedora/package.spec",
    }
    new_pc = PackageConfig.get_from_dict(di)
    pc = PackageConfig(
        dist_git_base_url="https://packit.dev/",
        downstream_package_name="packit",
        dist_git_namespace="awesome",
        synced_files=SyncFilesConfig(
            files_to_sync=[
                SyncFilesItem(src="fedora/foobar.spec", dest="fedora/foobar.spec")
            ]
        ),
        specfile_path=str(Path.cwd().joinpath("fedora/package.spec")),
    )
    assert new_pc.specfile_path.endswith("fedora/package.spec")
    assert pc.specfile_path.endswith("fedora/package.spec")
    assert pc == new_pc
    assert pc.dist_git_package_url == "https://packit.dev/awesome/packit.git"
    assert new_pc.dist_git_package_url == "https://packit.dev/awesome/packit.git"


@pytest.mark.parametrize(
    "content",
    [
        "---\nspecfile_path: packit.spec\n"
        "synced_files:\n"
        "  - packit.spec\n"
        "  - src: .packit.yaml\n"
        "    dest: .packit2.yaml",
        '{"specfile_path": "packit.spec", "synced_files": ["packit.spec", '
        '{"src": ".packit.yaml", "dest": ".packit2.yaml"}]}',
    ],
)
def test_get_packit_config_from_repo(content):
    flexmock(GitProject).should_receive("get_file_content").and_return(content)
    git_project = GitProject(repo="", service=GitService(), namespace="")
    config = get_packit_config_from_repo(sourcegit_project=git_project, ref="")
    assert isinstance(config, PackageConfig)
    assert Path(config.specfile_path).name == "packit.spec"
    assert config.synced_files == SyncFilesConfig(
        files_to_sync=[
            SyncFilesItem(src="packit.spec", dest="packit.spec"),
            SyncFilesItem(src=".packit.yaml", dest=".packit2.yaml"),
        ]
    )


def test_get_user_config(tmpdir):
    user_config_file_path = Path(tmpdir) / ".packit.yaml"
    user_config_file_path.write_text(
        "---\n"
        "debug: true\n"
        "fas_user: rambo\n"
        "keytab_path: './rambo.keytab'\n"
        "github_token: ra\n"
        "pagure_user_token: mb\n"
        "pagure_fork_token: o\n"
    )
    flexmock(os).should_receive("getenv").with_args("XDG_CONFIG_HOME").and_return(
        str(tmpdir)
    )
    config = Config.get_user_config()
    assert config.debug and isinstance(config.debug, bool)
    assert config.fas_user == "rambo"
    assert config.keytab_path == "./rambo.keytab"
    flexmock(os).should_receive("getenv").with_args("GITHUB_TOKEN", "").and_return(None)
    assert config.github_token == "ra"
    flexmock(os).should_receive("getenv").with_args("PAGURE_USER_TOKEN", "").and_return(
        None
    )
    assert config.pagure_user_token == "mb"
    flexmock(os).should_receive("getenv").with_args("PAGURE_FORK_TOKEN", "").and_return(
        None
    )
    assert config.pagure_fork_token == "o"


@pytest.mark.parametrize(
    "packit_files,expected",
    [
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="conftest.py", dest="conftest.py")]
            ),
            [SyncFilesItem(src="conftest.py", dest="conftest.py")],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="__init__.py", dest="__init__.py"),
                    SyncFilesItem(src="conftest.py", dest="conftest.py"),
                    SyncFilesItem(src="spellbook.py", dest="spellbook.py"),
                ]
            ),
            [
                SyncFilesItem(src="__init__.py", dest="__init__.py"),
                SyncFilesItem(src="conftest.py", dest="conftest.py"),
                SyncFilesItem(src="spellbook.py", dest="spellbook.py"),
            ],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="functional/", dest="tests")]
            ),
            [
                SyncFilesItem(src="functional/__init__.py", dest="tests"),
                SyncFilesItem(src="functional/test_srpm.py", dest="tests"),
            ],
        ),
        (
            SyncFilesConfig(files_to_sync=[SyncFilesItem(src="*.py", dest="tests")]),
            [
                SyncFilesItem(src="__init__.py", dest="tests"),
                SyncFilesItem(src="conftest.py", dest="tests"),
                SyncFilesItem(src="spellbook.py", dest="tests"),
            ],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="unit/test_u*.py", dest="units")]
            ),
            [SyncFilesItem(src="unit/test_utils.py", dest="units")],
        ),
        (
            SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="integration/test_u*.py", dest="units")
                ]
            ),
            [
                SyncFilesItem(src="integration/test_upstream.py", dest="units"),
                SyncFilesItem(src="integration/test_update.py", dest="units"),
            ],
        ),
    ],
)
def test_sync_files(packit_files, expected):
    with cwd(TESTS_DIR):
        pc = PackageConfig(
            dist_git_base_url="https://packit.dev/",
            downstream_package_name="packit",
            dist_git_namespace="awesome",
            specfile_path="fedora/package.spec",
            synced_files=packit_files,
        )
        get_wildcard_resolved_sync_files(pc)
        assert pc.synced_files
        assert set(expected).issubset(set(pc.synced_files.files_to_sync))
