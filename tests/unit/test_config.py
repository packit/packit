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
from ogr.abstract import GitProject, GitService

from packit.actions import ActionName
from packit.config import (
    JobConfig,
    PackageConfig,
    JobTriggerType,
    SyncFilesConfig,
    SyncFilesItem,
    get_package_config_from_repo,
    Config,
    JobType,
    JobNotifyType,
)
from packit.exceptions import PackitInvalidConfigException


def get_job_config_dict_simple():
    return {"job": "build", "trigger": "release", "notify": []}


def get_job_config_dict_full():
    return {
        "job": "propose_downstream",
        "trigger": "pull_request",
        "notify": ["pull_request_status"],
        "metadata": {"a": "b"},
    }


def get_job_config_simple():
    return JobConfig(
        job=JobType.build, trigger=JobTriggerType.release, notify=[], metadata={}
    )


def get_job_config_full():
    return JobConfig(
        job=JobType.propose_downstream,
        trigger=JobTriggerType.pull_request,
        notify=[JobNotifyType.pull_request_status],
        metadata={"a": "b"},
    )


@pytest.fixture()
def job_config_simple():
    return get_job_config_simple()


@pytest.fixture()
def job_config_full():
    return get_job_config_full()


def test_job_config_equal(job_config_simple):
    assert job_config_simple == job_config_simple


def test_job_config_not_equal(job_config_simple, job_config_full):
    assert job_config_simple != job_config_full


def test_job_config_blah():
    with pytest.raises(PackitInvalidConfigException) as ex:
        JobConfig.get_from_dict({"job": "asdqwe", "trigger": "salt", "notify": []})
    assert "'asdqwe' is not one of " in str(ex.value)


@pytest.mark.parametrize(
    "raw,is_valid",
    [
        ({}, False),
        ({"trigger": "release"}, False),
        ({"release_to": ["f28"]}, False),
        ([], False),
        ({"asd"}, False),
        (get_job_config_dict_simple(), True),
        (get_job_config_dict_full(), True),
    ],
)
def test_job_config_validate(raw, is_valid):
    if is_valid:
        JobConfig.validate(raw)
    else:
        with pytest.raises(PackitInvalidConfigException):
            JobConfig.validate(raw)


@pytest.mark.parametrize(
    "raw,expected_config",
    [
        (get_job_config_dict_simple(), get_job_config_simple()),
        (get_job_config_dict_full(), get_job_config_full()),
    ],
)
def test_job_config_parse(raw, expected_config):
    job_config = JobConfig.get_from_dict(raw_dict=raw)
    assert job_config == expected_config


def test_package_config_equal(job_config_simple):
    assert PackageConfig(
        specfile_path="fedora/package.spec",
        synced_files=SyncFilesConfig(
            files_to_sync=[SyncFilesItem(src="packit.yaml", dest="packit.yaml")]
        ),
        jobs=[job_config_simple],
    ) == PackageConfig(
        specfile_path="fedora/package.spec",
        synced_files=SyncFilesConfig(
            files_to_sync=[SyncFilesItem(src="packit.yaml", dest="packit.yaml")]
        ),
        jobs=[job_config_simple],
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
            jobs=[get_job_config_simple()],
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=SyncFilesConfig(
                files_to_sync=[SyncFilesItem(src="c", dest="c")]
            ),
            jobs=[get_job_config_simple()],
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="a", dest="a"),
                    SyncFilesItem(src="b", dest="b"),
                ]
            ),
            jobs=[get_job_config_full()],
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="c", dest="c"),
                    SyncFilesItem(src="d", dest="d"),
                ]
            ),
            jobs=[get_job_config_full()],
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="c", dest="c"),
                    SyncFilesItem(src="d", dest="d"),
                ]
            ),
            jobs=[get_job_config_full()],
        ),
    ],
)
def test_package_config_not_equal(not_equal_package_config):
    j = get_job_config_full()
    j.metadata["b"] = "c"
    assert (
        not PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="c", dest="c"),
                    SyncFilesItem(src="d", dest="d"),
                ]
            ),
            jobs=[j],
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
        ({"jobs": [{"trigger": "release", "job": "propose_downstream"}]}, False),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/foobar.spec"],
            },
            True,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/foobar.spec", "somefile", "somedirectory"],
                "jobs": [],
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
            },
            False,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "actions": ["actions" "has", "to", "be", "key", "value"],
                "jobs": [{"job": "asd", "trigger": "qwe"}],
            },
            False,
        ),
    ],
)
def test_package_config_validate(raw, is_valid):
    if not is_valid:
        with pytest.raises(PackitInvalidConfigException):
            PackageConfig.validate(raw)
    else:
        PackageConfig.validate(raw)


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
                "jobs": [get_job_config_dict_full()],
            },
            PackageConfig(
                specfile_path="fedora/package.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        )
                    ]
                ),
                jobs=[get_job_config_full()],
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
                "jobs": [get_job_config_dict_simple()],
            },
            PackageConfig(
                specfile_path="fedora/package.spec",
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
                jobs=[get_job_config_simple()],
            ),
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/package.spec"],
                "jobs": [get_job_config_dict_full()],
            },
            PackageConfig(
                specfile_path="fedora/package.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        )
                    ]
                ),
                jobs=[get_job_config_full()],
            ),
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/package.spec", "somefile"],
                "jobs": [get_job_config_dict_full()],
                "something": "stupid",
            },
            PackageConfig(
                specfile_path="fedora/package.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        ),
                        SyncFilesItem(src="somefile", dest="somefile"),
                    ]
                ),
                jobs=[get_job_config_full()],
            ),
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/package.spec"],
                "jobs": [get_job_config_dict_full()],
                "something": "stupid",
                "upstream_project_url": "https://github.com/asd/qwe",
                "upstream_project_name": "qwe",
                "dist_git_base_url": "https://something.wicked",
            },
            PackageConfig(
                specfile_path="fedora/package.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        )
                    ]
                ),
                jobs=[get_job_config_full()],
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
                specfile_path="fedora/package.spec",
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
        specfile_path="fedora/package.spec",
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
def test_get_package_config_from_repo(content):
    flexmock(GitProject).should_receive("get_file_content").and_return(content)
    git_project = GitProject(repo="", service=GitService(), namespace="")
    config = get_package_config_from_repo(sourcegit_project=git_project, ref="")
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
