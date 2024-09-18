# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy
from pathlib import Path, PosixPath
from typing import Optional

import pytest
from flexmock import flexmock
from github import GithubException
from marshmallow import ValidationError
from ogr.abstract import GitProject, GitService
from ogr.exceptions import GithubAPIException

import packit.config.package_config
from packit.actions import ActionName
from packit.config import (
    CommonPackageConfig,
    JobConfig,
    JobConfigTriggerType,
    JobType,
    get_package_config_from_repo,
)
from packit.config.package_config import (
    PackageConfig,
    find_remote_package_config,
    get_local_package_config,
    get_local_specfile_path,
    get_specfile_path_from_repo,
)
from packit.config.sources import SourcesItem
from packit.constants import CONFIG_FILE_NAMES
from packit.exceptions import PackitConfigException
from packit.schema import PackageConfigSchema
from packit.sync import SyncFilesItem
from tests.spellbook import SYNC_FILES, UP_OSBUILD
from tests.unit.config.test_config import (
    get_default_job_config,
    get_job_config_build_for_branch,
    get_job_config_dict_build_for_branch,
    get_job_config_dict_full,
    get_job_config_dict_simple,
    get_job_config_full,
    get_job_config_simple,
)


@pytest.fixture()
def job_config_simple():
    return get_job_config_simple()


@pytest.mark.parametrize(
    "files,expected",
    [(["foo.spec"], "foo.spec"), ([], None)],
)
def test_get_specfile_path_from_repo(files, expected):
    gp = flexmock(GitProject)
    gp.should_receive("full_repo_name").and_return("a/b")
    gp.should_receive("get_files").and_return(files)
    git_project = GitProject(repo="", service=GitService(), namespace="")
    assert get_specfile_path_from_repo(project=git_project) == expected


@pytest.mark.parametrize(
    "package_config, project",
    [
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                            ),
                        },
                    ),
                ],
            ),
            None,
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                                project="example",
                            ),
                        },
                    ),
                ],
            ),
            "example",
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.release,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                                project="example1",
                            ),
                        },
                    ),
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                                project="example2",
                            ),
                        },
                    ),
                ],
            ),
            "example1",
        ),
    ],
)
def test_project_from_copr_build_job(package_config, project):
    config_project_value = package_config.get_copr_build_project_value()
    assert config_project_value == project


@pytest.mark.parametrize(
    "package_config, expected",
    [
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                                dist_git_branches=[
                                    "example",
                                ],
                            ),
                        },
                    ),
                ],
            ),
            [
                "example",
            ],
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                                dist_git_branches=[
                                    "example1",
                                    "example2",
                                ],
                            ),
                        },
                    ),
                ],
            ),
            ["example1", "example2"],
        ),
        (
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="xxx",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.propose_downstream,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                specfile_path="xxx",
                            ),
                        },
                    ),
                ],
            ),
            [],
        ),
    ],
)
def test_dg_branches_from_propose_downstream_job(package_config, expected):
    branches = package_config.get_propose_downstream_dg_branches_value()
    assert branches == expected


def test_package_config_equal(job_config_simple):
    assert PackageConfig(
        packages={
            "package": CommonPackageConfig(
                specfile_path="fedora/package.spec",
                files_to_sync=[SyncFilesItem(src=["packit.yaml"], dest="packit.yaml")],
                downstream_package_name="package",
                create_pr=True,
            ),
        },
        jobs=[job_config_simple],
    ) == PackageConfig(
        packages={
            "package": CommonPackageConfig(
                specfile_path="fedora/package.spec",
                files_to_sync=[SyncFilesItem(src=["packit.yaml"], dest="packit.yaml")],
                downstream_package_name="package",
                create_pr=True,
            ),
        },
        jobs=[job_config_simple],
    )


@pytest.mark.parametrize(
    "not_equal_package_config",
    [
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/other-package.spec",
                    files_to_sync=[
                        SyncFilesItem(src=["a"], dest="a"),
                        SyncFilesItem(src=["b"], dest="b"),
                    ],
                ),
            },
            jobs=[get_job_config_simple()],
        ),
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    files_to_sync=[SyncFilesItem(src=["c"], dest="c")],
                ),
            },
            jobs=[get_job_config_simple()],
        ),
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    files_to_sync=[
                        SyncFilesItem(src=["a"], dest="a"),
                        SyncFilesItem(src=["b"], dest="b"),
                    ],
                ),
            },
            jobs=[get_job_config_full()],
        ),
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    files_to_sync=[
                        SyncFilesItem(src=["c"], dest="c"),
                        SyncFilesItem(src=["d"], dest="d"),
                    ],
                    create_pr=False,
                ),
            },
            jobs=[get_job_config_full()],
        ),
    ],
)
def test_package_config_not_equal(not_equal_package_config):
    config = PackageConfig(
        packages={
            "package": CommonPackageConfig(
                specfile_path="fedora/package.spec",
                files_to_sync=[
                    SyncFilesItem(src=["c"], dest="c"),
                    SyncFilesItem(src=["d"], dest="d"),
                ],
                create_pr=True,
            ),
        },
        jobs=[get_job_config_full()],
    )
    assert config != not_equal_package_config


@pytest.mark.parametrize(
    "raw,is_valid",
    [
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "files_to_sync": "fedora/foobar.spec",
            },
            False,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "files_to_sync": ["fedora/foobar.spec"],
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "files_to_sync": ["fedora/foobar.spec", "somefile", "somedirectory"],
                "jobs": [],
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "dist_git_branches": [
                            "fedora-all",
                        ],
                    },
                ],
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "dist_git_branches": ["fedora-all", "epel-8"],
                    },
                ],
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "release",
                        "targets": [
                            "fedora-stable",
                        ],
                    },
                ],
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "release",
                        "targets": ["fedora-stable", "fedora-development"],
                    },
                ],
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "targets": ["f31", "f32"],
                        "timeout": 123,
                        "owner": "santa",
                        "project": "gifts",
                    },
                ],
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "tests",
                        "trigger": "pull_request",
                        "targets": [
                            "fedora-all",
                        ],
                        "env": {
                            "MYVAR1": 5,
                            "MYVAR2": "foo",
                        },
                    },
                ],
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "files_to_sync": ["fedora/foobar.spec"],
                "actions": {
                    "pre-sync": "some/pre-sync/command --option",
                    "get-current-version": "get-me-version",
                },
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "files_to_sync": ["fedora/foobar.spec"],
                "actions": {
                    "pre-sync": "some/pre-sync/command --option",
                    "unknown-action": "nothing",
                },
            },
            False,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "actions": ["actions" "has", "to", "be", "key", "value"],
                "jobs": [{"job": "asd", "trigger": "qwe"}],
            },
            False,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "notifications": {"pull_request": {"successful_build": False}},
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "notifications": {
                    "pull_request": {"successful_build": False},
                    "failure_comment": {"message": "my comment"},
                },
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "notifications": {"failure_comment": {"message": "my comment"}},
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "notifications": {"pull_request": {"successful_build": "nie"}},
            },
            False,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "notifications": {"pull_request": False},
            },
            False,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "sources": [{"path": "example_path"}],
            },
            False,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "sources": [{"url": "example_url"}],
            },
            False,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "sources": {"path": "example_path", "url": "example_url"},
            },
            False,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "release",
                        "targets": [
                            "fedora-stable",
                        ],
                        "module_hotfixes": True,
                    },
                ],
            },
            True,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "release",
                        "targets": [
                            "fedora-stable",
                        ],
                        "module_hotfixes": True,
                        "status_name_template": "packit-copr-build-release",
                    },
                ],
            },
            True,
        ),
    ],
)
def test_package_config_validate(raw, is_valid):
    if not is_valid:
        with pytest.raises((ValidationError, ValueError)):
            PackageConfig.get_from_dict(raw)
    else:
        PackageConfig.get_from_dict(raw)


@pytest.mark.parametrize(
    "raw,is_valid",
    [
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "unknown": "key",
                    },
                ],
            },
            False,
        ),
        (
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "unknown": "key",
                    },
                ],
            },
            False,
        ),
    ],
)
def test_package_config_validate_unknown_key(raw, is_valid):
    if not is_valid:
        with pytest.raises((ValidationError, ValueError)):
            PackageConfig.get_from_dict(raw)
    else:
        PackageConfig.get_from_dict(raw)


@pytest.mark.parametrize(
    "raw",
    [
        # {"specfile_path": "test/spec/file/path", "something": "different"},
        {
            "specfile_path": "test/spec/file/path",
            "jobs": [{"trigger": "release", "release_to": ["f28"]}],
        },
    ],
)
def test_package_config_parse_error(raw):
    with pytest.raises(Exception):
        PackageConfig.get_from_dict(raw_dict=raw)


@pytest.mark.parametrize(
    "raw,expected",
    [
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "files_to_sync": ["fedora/package.spec"],
                "jobs": [get_job_config_dict_full()],
                "downstream_package_name": "package",
                "create_pr": False,
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="fedora/package.spec",
                        downstream_package_name="package",
                        create_pr=False,
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                        ],
                    ),
                },
                jobs=[
                    get_job_config_full(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        create_pr=False,
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                        ],
                    ),
                ],
            ),
            id="specfile_path+files_to_sync+job_config_full+downstream_package_name+create_pr",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "files_to_sync": [
                    "fedora/package.spec",
                    "somefile",
                    "other",
                    "directory/files",
                ],
                "jobs": [get_job_config_dict_simple()],
                "downstream_package_name": "package",
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                            SyncFilesItem(src=["somefile"], dest="somefile"),
                            SyncFilesItem(src=["other"], dest="other"),
                            SyncFilesItem(
                                src=["directory/files"],
                                dest="directory/files",
                            ),
                        ],
                    ),
                },
                jobs=[
                    get_job_config_simple(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                            SyncFilesItem(src=["somefile"], dest="somefile"),
                            SyncFilesItem(src=["other"], dest="other"),
                            SyncFilesItem(
                                src=["directory/files"],
                                dest="directory/files",
                            ),
                        ],
                    ),
                ],
            ),
            id="specfile_path+files_to_sync+job_config_dict_simple+downstream_package_name",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "files_to_sync": ["fedora/package.spec"],
                "jobs": [get_job_config_dict_full()],
                "downstream_package_name": "package",
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                        ],
                    ),
                },
                jobs=[
                    get_job_config_full(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                        ],
                    ),
                ],
            ),
            id="specfile_path+files_to_sync(spec_only)+job_config_full+downstream_package_name",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "files_to_sync": ["fedora/package.spec", "somefile"],
                "jobs": [get_job_config_dict_full()],
                "downstream_package_name": "package",
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                            SyncFilesItem(src=["somefile"], dest="somefile"),
                        ],
                    ),
                },
                jobs=[
                    get_job_config_full(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                            SyncFilesItem(src=["somefile"], dest="somefile"),
                        ],
                    ),
                ],
            ),
            id="specfile_path+files_to_sync+job_config_full+downstream_package_name",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "files_to_sync": ["fedora/package.spec"],
                "jobs": [get_job_config_dict_full()],
                "upstream_project_url": "https://github.com/asd/qwe",
                "upstream_package_name": "qwe",
                "dist_git_base_url": "https://something.wicked",
                "downstream_package_name": "package",
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        upstream_project_url="https://github.com/asd/qwe",
                        upstream_package_name="qwe",
                        dist_git_base_url="https://something.wicked",
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                        ],
                    ),
                },
                jobs=[
                    get_job_config_full(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        upstream_project_url="https://github.com/asd/qwe",
                        upstream_package_name="qwe",
                        dist_git_base_url="https://something.wicked",
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                        ],
                    ),
                ],
            ),
            id="specfile_path+files_to_sync+job_config_dict_full+upstream_project_url"
            "+upstream_package_name+dist_git_base_url+downstream_package_name",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "actions": {
                    "pre-sync": "some/pre-sync/command --option",
                    "get-current-version": "get-me-version",
                },
                "jobs": [],
                "upstream_project_url": "https://github.com/asd/qwe",
                "upstream_package_name": "qwe",
                "dist_git_base_url": "https://something.wicked",
                "downstream_package_name": "package",
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="fedora/package.spec",
                        actions={
                            ActionName.pre_sync: "some/pre-sync/command --option",
                            ActionName.get_current_version: "get-me-version",
                        },
                        upstream_project_url="https://github.com/asd/qwe",
                        upstream_package_name="qwe",
                        dist_git_base_url="https://something.wicked",
                        downstream_package_name="package",
                    ),
                },
                jobs=[],
            ),
            id="specfile_path+actions+empty_jobs+upstream_project_url"
            "+upstream_package_name+dist_git_base_url+downstream_package_name",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "files_to_sync": ["fedora/package.spec"],
                "downstream_package_name": "package",
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                        ],
                    ),
                },
                jobs=get_default_job_config(
                    downstream_package_name="package",
                    specfile_path="fedora/package.spec",
                    files_to_sync=[
                        SyncFilesItem(
                            src=["fedora/package.spec"],
                            dest="fedora/package.spec",
                        ),
                    ],
                ),
            ),
            id="specfile_path+files_to_sync+downstream_package_name",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "spec_source_id": 3,
                "jobs": [get_job_config_dict_build_for_branch()],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        spec_source_id="Source3",
                    ),
                },
                jobs=[
                    get_job_config_build_for_branch(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        spec_source_id="Source3",
                    ),
                ],
            ),
            id="specfile_path+get_job_config_dict_build_for_branch",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "sync_changelog": True,
                "jobs": [get_job_config_dict_simple()],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        sync_changelog=True,
                    ),
                },
                jobs=[
                    get_job_config_simple(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        sync_changelog=True,
                    ),
                ],
            ),
            id="sync_changelog_true",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [get_job_config_dict_simple()],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        sync_changelog=False,
                    ),
                },
                jobs=[
                    get_job_config_simple(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        sync_changelog=False,
                    ),
                ],
            ),
            id="sync_changelog_false_by_default",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "create_sync_note": False,
                "jobs": [get_job_config_dict_simple()],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        create_sync_note=False,
                    ),
                },
                jobs=[
                    get_job_config_simple(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        create_sync_note=False,
                    ),
                ],
            ),
            id="create_sync_note_false",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [get_job_config_dict_simple()],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        create_sync_note=True,
                    ),
                },
                jobs=[
                    get_job_config_simple(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        create_sync_note=True,
                    ),
                ],
            ),
            id="create_sync_note_true_by_default",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "sources": [
                    {
                        "path": "rsync-3.1.3.tar.gz",
                        "url": "https://git.centos.org/sources/rsync/c8s/82e7829",
                    },
                ],
                "jobs": [],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        sources=[
                            SourcesItem(
                                path="rsync-3.1.3.tar.gz",
                                url="https://git.centos.org/sources/rsync/c8s/82e7829",
                            ),
                        ],
                    ),
                },
                jobs=[],
            ),
            id="sources",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "release",
                        "fmf_url": "https://example.com",
                        "fmf_ref": "test_ref",
                        "fmf_path": "test/path",
                    },
                ],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        sync_changelog=False,
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.release,
                        packages={
                            "package": CommonPackageConfig(
                                downstream_package_name="package",
                                specfile_path="fedora/package.spec",
                                sync_changelog=False,
                                fmf_url="https://example.com",
                                fmf_ref="test_ref",
                                fmf_path="test/path",
                            ),
                        },
                    ),
                ],
            ),
            id="sync_changelog_false_by_default",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "release",
                        "tmt_plan": "^packit!",
                        "tf_post_install_script": "echo 'hi packit!'",
                    },
                ],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        sync_changelog=False,
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.release,
                        packages={
                            "package": CommonPackageConfig(
                                downstream_package_name="package",
                                specfile_path="fedora/package.spec",
                                sync_changelog=False,
                                tmt_plan="^packit!",
                                tf_post_install_script="echo 'hi packit!'",
                            ),
                        },
                    ),
                ],
            ),
            id="extra_tf_api_parameters",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "release",
                        "tf_extra_params": {
                            "environments": [
                                {
                                    "pool": "new-pool",
                                    "tmt": {
                                        "context": {
                                            "how": "full",
                                        },
                                    },
                                },
                            ],
                            "test": {"fmf": {"name": "foo"}},
                        },
                    },
                ],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        sync_changelog=False,
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.release,
                        packages={
                            "package": CommonPackageConfig(
                                downstream_package_name="package",
                                specfile_path="fedora/package.spec",
                                sync_changelog=False,
                                tf_extra_params={
                                    "environments": [
                                        {
                                            "pool": "new-pool",
                                            "tmt": {"context": {"how": "full"}},
                                        },
                                    ],
                                    "test": {"fmf": {"name": "foo"}},
                                },
                            ),
                        },
                    ),
                ],
            ),
            id="extra_tf_api_parameters_freeform",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "vm_image_build",
                        "trigger": "pull_request",
                        "image_distribution": "rhel-90",
                        "image_request": {
                            "architecture": "x86_64",
                            "image_type": "aws",
                            "upload_request": {
                                "options": {"share_with_accounts": ["123456789012"]},
                                "type": "aws",
                            },
                        },
                        "image_customizations": {
                            "packages": ["peddle", "board"],
                        },
                    },
                ],
            },
            PackageConfig(
                # parsing makes it inherit: in here we need to be explicit
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.vm_image_build,
                        trigger=JobConfigTriggerType.pull_request,
                        packages={
                            "package": CommonPackageConfig(
                                downstream_package_name="package",
                                specfile_path="fedora/package.spec",
                                image_distribution="rhel-90",
                                image_request={
                                    "architecture": "x86_64",
                                    "image_type": "aws",
                                    "upload_request": {
                                        "options": {
                                            "share_with_accounts": ["123456789012"],
                                        },
                                        "type": "aws",
                                    },
                                },
                                image_customizations={
                                    "packages": ["peddle", "board"],
                                },
                            ),
                        },
                    ),
                ],
            ),
            id="vm-image-build",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "koji_build",
                        "trigger": "commit | koji_build",
                        "sidetag_group": "test",
                        "dependencies": ["some-package"],
                        "dist_git_branches": ["fedora-all"],
                    },
                ],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.koji_build,
                        trigger=JobConfigTriggerType.commit,
                        sidetag_group="test",
                        dependencies=["some-package"],
                        packages={
                            "package": CommonPackageConfig(
                                downstream_package_name="package",
                                specfile_path="fedora/package.spec",
                                dist_git_branches=["fedora-all"],
                            ),
                        },
                    ),
                    JobConfig(
                        type=JobType.koji_build,
                        trigger=JobConfigTriggerType.koji_build,
                        sidetag_group="test",
                        dependencies=["some-package"],
                        packages={
                            "package": CommonPackageConfig(
                                downstream_package_name="package",
                                specfile_path="fedora/package.spec",
                                dist_git_branches=["fedora-all"],
                            ),
                        },
                    ),
                ],
            ),
            id="koji_build_with_multiple_triggers",
        ),
    ],
)
def test_package_config_parse(raw, expected):
    package_config = PackageConfig.get_from_dict(raw_dict=raw)
    assert package_config
    # tests for https://github.com/packit/packit-service/pull/342
    if expected.jobs:
        for j in package_config.jobs:
            assert j.type
    assert package_config == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "release",
                        "specfile_path": "somewhere/package.spec",
                    },
                ],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.release,
                        packages={
                            "package": CommonPackageConfig(
                                downstream_package_name="package",
                                specfile_path="somewhere/package.spec",
                            ),
                        },
                    ),
                ],
            ),
            id="override-specfile_path",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "files_to_sync": ["x", "y"],
                "actions": {"post-upstream-clone": "ls"},
                "spec_source_id": "Source0",
                "targets": ["fedora-36"],
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "release",
                        "specfile_path": "somewhere/package.spec",
                        "files_to_sync": ["a", "b", "c"],
                        "actions": {"create-archive": "ls"},
                        "spec_source_id": "Source1",
                    },
                ],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        files_to_sync=[SyncFilesItem([x], x) for x in ("x", "y")],
                        actions={ActionName.post_upstream_clone: "ls"},
                        _targets=["fedora-36"],
                    ),
                },
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.release,
                        packages={
                            "package": CommonPackageConfig(
                                downstream_package_name="package",
                                specfile_path="somewhere/package.spec",
                                files_to_sync=[
                                    SyncFilesItem([x], x) for x in ("a", "b", "c")
                                ],
                                actions={ActionName.create_archive: "ls"},
                                _targets=["fedora-36"],
                                spec_source_id="Source1",
                            ),
                        },
                    ),
                ],
            ),
            id="override-alot",
        ),
    ],
)
def test_package_config_overrides(raw, expected):
    package_config = PackageConfig.get_from_dict(raw_dict=raw)
    assert package_config == expected


@pytest.mark.parametrize(
    "raw,err_message",
    [
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [{"job": "build", "trigger": "release", "actions": ["a"]}],
            },
            "'dict' required, got <class 'list'>.",
            id="bad_actions",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "fedora/package.spec",
                "jobs": [{"job": "build", "trigger": "release", "files_to_sync": "a"}],
            },
            "ValidationError",
            id="bad_files_to_sync",
        ),
    ],
)
def test_package_config_overrides_bad(raw, err_message):
    with pytest.raises(ValidationError) as ex:
        PackageConfig.get_from_dict(raw_dict=raw)
    assert err_message in str(ex)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            {
                "specfile_path": "fedora/package.spec",
                "files_to_sync": ["fedora/package.spec"],
                "jobs": [],
            },
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="fedora/package.spec",
                        files_to_sync=[
                            SyncFilesItem(
                                src=["fedora/package.spec"],
                                dest="fedora/package.spec",
                            ),
                        ],
                        downstream_package_name="package",
                        upstream_package_name="package",
                    ),
                },
            ),
        ),
    ],
)
def test_package_config_upstream_and_downstream_package_names(raw, expected):
    package_config = PackageConfig.get_from_dict(raw_dict=raw, repo_name="package")
    assert package_config
    assert package_config == expected


def test_dist_git_package_url():
    di = {
        "dist_git_base_url": "https://packit.dev/",
        "downstream_package_name": "packit",
        "dist_git_namespace": "awesome",
        "files_to_sync": ["fedora/foobar.spec"],
        "specfile_path": "fedora/package.spec",
        "create_pr": False,
    }
    new_pc = PackageConfig.get_from_dict(di)
    pc = PackageConfig(
        packages={
            "packit": CommonPackageConfig(
                dist_git_base_url="https://packit.dev/",
                downstream_package_name="packit",
                dist_git_namespace="awesome",
                files_to_sync=[
                    SyncFilesItem(
                        src=["fedora/foobar.spec"],
                        dest="fedora/foobar.spec",
                    ),
                ],
                specfile_path="fedora/package.spec",
                create_pr=False,
            ),
        },
        jobs=get_default_job_config(
            dist_git_base_url="https://packit.dev/",
            downstream_package_name="packit",
            dist_git_namespace="awesome",
            files_to_sync=[
                SyncFilesItem(src=["fedora/foobar.spec"], dest="fedora/foobar.spec"),
            ],
            specfile_path="fedora/package.spec",
            create_pr=False,
        ),
    )
    assert new_pc.specfile_path.endswith("fedora/package.spec")
    assert pc.specfile_path.endswith("fedora/package.spec")
    assert pc == new_pc
    assert pc.dist_git_package_url == "https://packit.dev/awesome/packit.git"
    assert new_pc.dist_git_package_url == "https://packit.dev/awesome/packit.git"
    assert not pc.create_pr


@pytest.mark.parametrize(
    "files,config_name,content,project,spec_path",
    [
        (
            [".packit.yaml", "tox.ini", "setup.py", "packit.spec"],
            ".packit.yaml",
            "files_to_sync:\n"
            "  - packit.spec\n"
            "  - src: {config_name}\n"
            "    dest: .packit2.yaml",
            flexmock(repo="packit"),
            "packit.spec",
        ),
        (
            ["packit.yml", "tox.ini", "setup.py", "packit.spec"],
            "packit.yml",
            "files_to_sync:\n"
            "  - packit.spec\n"
            "  - src: {config_name}\n"
            "    dest: .packit2.yaml",
            flexmock(repo="packit"),
            "packit.spec",
        ),
        (
            ["setup.cfg", "setup.py", "packit.spec", ".zuul.yaml"],
            None,
            "",
            flexmock(repo="packit"),
            "packit.spec",
        ),
    ],
)
def test_get_package_config_from_repo(
    files,
    config_name,
    content,
    project,
    spec_path: Optional[str],
):
    if config_name:
        project.should_receive("get_files").and_return([spec_path]).once()
        project.should_receive("get_file_content").with_args(
            path=config_name,
            ref=None,
        ).and_return(content.format(config_name=config_name)).once()
    project.should_receive("full_repo_name").and_return("a/b")
    project.should_receive("get_files").with_args(ref=None, recursive=False).and_return(
        files,
    )
    config = get_package_config_from_repo(project=project)
    if config_name:
        assert isinstance(config, PackageConfig)
        assert config.specfile_path == spec_path
        assert config.files_to_sync == [
            SyncFilesItem(src=["packit.spec"], dest="packit.spec"),
            SyncFilesItem(src=[config_name], dest=".packit2.yaml"),
        ]
        assert config.create_pr
    else:
        assert config is None


def test_get_package_config_from_repo_explicit_path():
    """Test getting the package config when the path is explicitly specified"""
    project = flexmock(repo="packit")
    config_name = ".distro/source-git.yaml"

    project.should_receive("get_file_content").with_args(
        path=config_name,
        ref=None,
    ).and_return(
        """\
upstream_project_url: https://github.com/packit/packit
downstream_package_name: packit
specfile_path: ".distro/packit.spec"
files_to_sync:
- src: .distro/
  dest: .
  delete: true
  filters:
  - "protect .git*"
  - "protect sources"
  - "exclude source-git.yaml"
  - "exclude .gitignore"
""",
    ).once()
    project.should_receive("full_repo_name").and_return("packit/packit")
    config = get_package_config_from_repo(
        project=project,
        package_config_path=config_name,
    )
    assert config is not None
    assert config.downstream_package_name == "packit"
    assert config.upstream_project_url == "https://github.com/packit/packit"
    assert config.specfile_path == ".distro/packit.spec"


def test_get_package_config_from_repo_empty_no_spec():
    gp = flexmock(GitProject)
    gp.should_receive("get_files").and_return([])
    gp.should_receive("full_repo_name").and_return("a/b")
    gp.should_receive("get_file_content").and_return("# this is a comment")
    gp.should_receive("get_files").with_args(ref=None, recursive=False).and_return(
        ["packit.yaml", "tox.ini"],
    )
    git_project = GitProject(repo="packit", service=GitService(), namespace="")
    with pytest.raises(
        PackitConfigException,
        match="specfile_path' is not specified or no specfile was found in the repo",
    ):
        get_package_config_from_repo(project=git_project)


@pytest.mark.parametrize(
    "content, specfile_path",
    [
        ("{}", "packit.spec"),
        ("{jobs: [{job: copr_build, trigger: commit}]}", "packit.spec"),
        (
            "{downstream_package_name: horkyze, jobs: [{job: copr_build, trigger: commit}]}",
            "horkyze.spec",
        ),
        (
            "{upstream_package_name: slize, jobs: [{job: copr_build, trigger: commit}]}",
            "packit.spec",
        ),
    ],
)
def test_get_package_config_from_repo_spec_file_not_defined(content, specfile_path):
    gp = flexmock(GitProject)
    gp.should_receive("get_files").and_return([specfile_path])
    gp.should_receive("full_repo_name").and_return("a/b")
    gp.should_receive("get_file_content").and_return(content)
    gp.should_receive("get_files").with_args(ref=None, recursive=False).and_return(
        ["packit.yaml", "tox.ini"],
    )
    git_project = GitProject(repo="packit", service=GitService(), namespace="")
    config = get_package_config_from_repo(project=git_project)
    assert isinstance(config, PackageConfig)
    assert config.specfile_path == specfile_path
    assert config.create_pr
    for j in config.jobs:
        assert j.specfile_path == specfile_path
        assert j.downstream_package_name == config.downstream_package_name
        assert j.upstream_package_name == config.upstream_package_name


def test_notifications_section():
    pc = PackageConfig.get_from_dict(
        {"specfile_path": "package.spec"},
        repo_name="package",
    )
    assert not pc.notifications.pull_request.successful_build
    assert pc.notifications.failure_issue.create
    assert pc.notifications.failure_comment.message is None


def test_notifications_section_failure_comment_message():
    message = "my message"
    pc = PackageConfig.get_from_dict(
        {
            "specfile_path": "package.spec",
            "notifications": {"failure_comment": {"message": message}},
        },
        repo_name="package",
    )
    assert not pc.notifications.pull_request.successful_build
    assert pc.notifications.failure_issue.create
    assert pc.notifications.failure_comment.message == message


def test_notifications_section_failure_issue_create_false():
    pc = PackageConfig.get_from_dict(
        {
            "specfile_path": "package.spec",
            "notifications": {"failure_issue": {"create": False}},
        },
        repo_name="package",
    )
    assert not pc.notifications.pull_request.successful_build
    assert not pc.notifications.failure_issue.create


def test_test_command_labels():
    labels = ["label1", "label2"]
    pc = PackageConfig.get_from_dict(
        {
            "specfile_path": "package.spec",
            "test_command": {"default_labels": labels},
        },
        repo_name="package",
    )
    assert pc.test_command.default_labels == labels
    assert not pc.test_command.default_identifier


@pytest.mark.parametrize(
    "package_config_dict, present, absent",
    [
        (
            {
                "specfile_path": "package.spec",
            },
            [],
            [],
        ),
        (
            {"specfile_path": "package.spec", "require": {}},
            [],
            [],
        ),
        (
            {"specfile_path": "package.spec", "require": {"label": {}}},
            [],
            [],
        ),
        (
            {
                "specfile_path": "package.spec",
                "require": {
                    "label": {"present": ["label-1"]},
                },
            },
            ["label-1"],
            [],
        ),
        (
            {
                "specfile_path": "package.spec",
                "require": {
                    "label": {"absent": ["label-1"]},
                },
            },
            [],
            ["label-1"],
        ),
        (
            {
                "specfile_path": "package.spec",
                "require": {
                    "label": {"present": ["label-1"], "absent": ["label-2", "label-3"]},
                },
            },
            ["label-1"],
            ["label-2", "label-3"],
        ),
    ],
)
def test_require(package_config_dict, present, absent):
    pc = PackageConfig.get_from_dict(
        package_config_dict,
        repo_name="package",
    )
    assert pc.require.label.present == present
    assert pc.require.label.absent == absent


def test_test_command_identifiers():
    identifier = "id1"
    pc = PackageConfig.get_from_dict(
        {
            "specfile_path": "package.spec",
            "test_command": {"default_identifier": identifier},
        },
        repo_name="package",
    )
    assert not pc.test_command.default_labels
    assert pc.test_command.default_identifier == identifier


def test_get_raw_dict_with_defaults():
    pc = PackageConfig.get_from_dict(
        {
            "specfile_path": "package.spec",
        },
        repo_name="package",
        config_file_path="path",
    )
    assert pc.get_raw_dict_with_defaults() == {
        "specfile_path": "package.spec",
        "config_file_path": "path",
        "upstream_package_name": "package",
        "downstream_package_name": "package",
    }


def test_get_local_specfile_path():
    assert str(get_local_specfile_path(UP_OSBUILD)) == "osbuild.spec"
    assert not get_local_specfile_path(SYNC_FILES)


@pytest.mark.parametrize(
    "directory, local_first,local_last,config_file_name,res_pc_path",
    [
        ([], False, True, None, Path.cwd() / next(iter(CONFIG_FILE_NAMES))),
        ([], False, False, "different_conf.yaml", "different_conf.yaml"),
    ],
)
def test_get_local_package_config_path(
    directory,
    local_first,
    local_last,
    config_file_name,
    res_pc_path,
):
    flexmock(PosixPath).should_receive("is_file").and_return(True)

    (
        flexmock(packit.config.package_config)
        .should_receive("load_packit_yaml")
        .with_args(Path(res_pc_path))
        .and_return(None)
    )

    (
        flexmock(packit.config.package_config)
        .should_receive("parse_loaded_config")
        .and_return(None)
    )

    get_local_package_config(
        try_local_dir_last=local_last,
        package_config_path=config_file_name,
    )


def test_specfile_path_from_downstream_package_name():
    """
    If 'downstream_package_name' is set in the package configuration,
    'specfile_path' is set to '{downstream_package_name}.spec'
    """
    (
        flexmock(packit.config.package_config)
        .should_receive("load_packit_yaml")
        .and_return({"downstream_package_name": "cockpit"})
    )
    assert (
        get_local_package_config(
            package_config_path=".packit.yaml",
            repo_name="cockpit",
        ).specfile_path
        == PackageConfig(
            packages={"cockpit": CommonPackageConfig(specfile_path="cockpit.spec")},
        ).specfile_path
    )


@pytest.mark.parametrize(
    "package_config",
    [
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    downstream_package_name="package",
                    upstream_package_name="package",
                    files_to_sync=[
                        SyncFilesItem(
                            src=["fedora/package.spec"],
                            dest="fedora/package.spec",
                        ),
                    ],
                ),
            },
        ),
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    downstream_package_name="package",
                    upstream_package_name="package",
                    files_to_sync=[
                        SyncFilesItem(
                            src=["fedora/package.spec"],
                            dest="fedora/package.spec",
                        ),
                    ],
                ),
            },
        ),
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    downstream_package_name="package",
                    upstream_package_name="package",
                    files_to_sync=[
                        SyncFilesItem(
                            src=["fedora/package.spec"],
                            dest="fedora/package.spec",
                        ),
                    ],
                ),
            },
        ),
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    downstream_package_name="package",
                    files_to_sync=[
                        SyncFilesItem(
                            src=["fedora/package.spec"],
                            dest="fedora/package.spec",
                        ),
                    ],
                ),
            },
            jobs=[
                get_job_config_full(
                    specfile_path="fedora/package.spec",
                    downstream_package_name="package",
                    files_to_sync=[
                        SyncFilesItem(
                            src=["fedora/package.spec"],
                            dest="fedora/package.spec",
                        ),
                    ],
                ),
            ],
        ),
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    actions={
                        ActionName.pre_sync: "some/pre-sync/command --option",
                        ActionName.get_current_version: "get-me-version",
                    },
                    upstream_project_url="https://github.com/asd/qwe",
                    upstream_package_name="qwe",
                    dist_git_base_url="https://something.wicked",
                    downstream_package_name="package",
                    spec_source_id="Source1",
                ),
            },
            jobs=[],
        ),
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    actions={
                        ActionName.pre_sync: "some/pre-sync/command --option",
                        ActionName.get_current_version: "get-me-version",
                    },
                    upstream_project_url="https://github.com/asd/qwe",
                    upstream_package_name="qwe",
                    dist_git_base_url="https://something.wicked",
                    downstream_package_name="package",
                    spec_source_id="Source1",
                    sources=[
                        SourcesItem(
                            path="rsync-3.1.3.tar.gz",
                            url="https://git.centos.org/sources/rsync/c8s/82e7829",
                        ),
                    ],
                ),
            },
            jobs=[],
        ),
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    actions={
                        ActionName.pre_sync: "some/pre-sync/command --option",
                        ActionName.get_current_version: "get-me-version",
                    },
                    upstream_project_url="https://github.com/asd/qwe",
                    upstream_package_name="qwe",
                    srpm_build_deps=["make", "tar", "findutils"],
                ),
            },
            jobs=[],
        ),
        PackageConfig(
            packages={
                "main": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    upstream_project_url="https://github.com/asd/qwe",
                    upstream_package_name="qwe",
                    srpm_build_deps=[],
                    status_name_template="packit-job",
                ),
            },
            jobs=[],
        ),
    ],
)
def test_serialize_and_deserialize(package_config):
    schema = PackageConfigSchema()
    serialized = schema.dump(package_config)
    new_package_config = schema.load(serialized)
    assert package_config == new_package_config


@pytest.mark.parametrize(
    "package_config",
    [
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    specfile_path="fedora/package.spec",
                    config_file_path=".packit.yaml",
                    downstream_package_name="package",
                    upstream_package_name="package",
                    files_to_sync=[
                        SyncFilesItem(
                            src=["fedora/package.spec"],
                            dest="fedora/package.spec",
                        ),
                        SyncFilesItem(
                            src=[".packit.yaml"],
                            dest=".packit.yaml",
                        ),
                    ],
                ),
            },
        ),
    ],
)
def test_files_to_sync_after_dump(package_config):
    schema = PackageConfigSchema()
    assert len(package_config.files_to_sync) == 2
    serialized = schema.dump(package_config)
    new_package_config = schema.load(serialized)
    assert len(new_package_config.files_to_sync) == 2


def test_get_specfile_sync_files_item():
    pc = PackageConfig(
        packages={
            "ogr": CommonPackageConfig(
                specfile_path="fedora/python-ogr.spec",
                downstream_package_name="python-ogr",
            ),
        },
    )
    upstream_specfile_path = "fedora/python-ogr.spec"
    downstream_specfile_path = "python-ogr.spec"

    assert pc.get_specfile_sync_files_item() == SyncFilesItem(
        src=[upstream_specfile_path],
        dest=downstream_specfile_path,
    )
    assert pc.get_specfile_sync_files_item(from_downstream=True) == SyncFilesItem(
        src=[downstream_specfile_path],
        dest=upstream_specfile_path,
    )


def test_get_specfile_sync_files_nodownstreamname_item():
    pc = PackageConfig(
        packages={
            "package": CommonPackageConfig(specfile_path="fedora/python-ogr.spec"),
        },
    )
    upstream_specfile_path = "fedora/python-ogr.spec"
    downstream_specfile_path = "python-ogr.spec"

    assert pc.get_specfile_sync_files_item() == SyncFilesItem(
        src=[upstream_specfile_path],
        dest=downstream_specfile_path,
    )
    assert pc.get_specfile_sync_files_item(from_downstream=True) == SyncFilesItem(
        src=[downstream_specfile_path],
        dest=upstream_specfile_path,
    )


@pytest.mark.parametrize(
    "raw",
    [
        {
            "packages": {"package": {}},
            "jobs": [
                {
                    "job": "copr_build",
                    "trigger": "release",
                    "targets": ["fedora-stable", "fedora-development"],
                },
            ],
        },
        {
            "packages": {"package": {}},
            "jobs": [
                {
                    "job": "tests",
                    "trigger": "release",
                    "targets": ["fedora-stable", "fedora-development"],
                },
            ],
        },
    ],
)
def test_package_config_specfile_not_present_raise(raw):
    with pytest.raises(ValidationError, match="'specfile_path' is not specified"):
        PackageConfig.get_from_dict(raw_dict=raw)


@pytest.mark.parametrize(
    "raw",
    [
        {
            "jobs": [
                {
                    "job": "tests",
                    "trigger": "commit",
                    "targets": ["fedora-stable", "fedora-development"],
                    "skip_build": True,
                    "manual_trigger": True,
                },
            ],
        },
        {
            "jobs": [
                {
                    "job": "tests",
                    "trigger": "commit",
                    "targets": ["fedora-stable", "fedora-development"],
                    "skip_build": True,
                    "manual_trigger": True,
                },
                {
                    "job": "tests",
                    "trigger": "pull_request",
                    "metadata": {
                        "targets": ["fedora-stable", "fedora-development"],
                        "skip_build": True,
                    },
                },
            ],
        },
    ],
)
def test_specfile_path_not_defined_in_test_only_jobs(raw):
    """Packages in test jobs, which are configured to not to require building
    a package don't need a 'specfile_path' set.

    Note: don't set 'downstream_package_name' either, as that implicitly sets
    'specfile_path' :-)
    """
    assert PackageConfig.get_from_dict(raw_dict=raw, repo_name="package")


@pytest.mark.parametrize(
    "package_name,result",
    ((None, None), ("baz", "https://foo/bar/baz.git")),
)
def test_pc_dist_git_package_url_has_no_None(package_name, result):
    assert (
        PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    downstream_package_name=package_name,
                    dist_git_base_url="https://foo/",
                    dist_git_namespace="bar",
                ),
            },
        ).dist_git_package_url
        == result
    )


def test_deepcopy():
    """Make sure the config object can be deepcopied"""
    d = {"package_config": PackageConfig(packages={"package": CommonPackageConfig()})}
    copy.deepcopy(d)


def test_load_is_not_destructive():
    """Check that the data loaded by PackageConfigSchema is not modified,
    and stays as it was passed for loading.
    """
    data = {"downstream_package_name": "package", "specfile_path": "package.spec"}
    original = copy.deepcopy(data)
    PackageConfigSchema().load(data)
    assert data == original


def test_handle_metadata():
    """Check that the deprecated 'metadata' field in 'jobs' is handled
    correctly.
    """
    data = {
        "downstream_package_name": "package",
        "specfile_path": "package.spec",
        "jobs": [
            {
                "job": "copr_build",
                "trigger": "pull_request",
                "metadata": {
                    "dist-git-branch": "shrek",
                },
            },
        ],
    }
    pc = PackageConfigSchema().load(data)
    assert pc.jobs[0].dist_git_branches == ["shrek"]


@pytest.mark.parametrize(
    "config",
    [
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "package.spec",
                "upstream_project_name": "upstream_package",
            },
            id="top_level",
        ),
    ],
)
@pytest.mark.skip(
    "upstream_project_name was renamed in upstream_package_name"
    "but now it is no more a deprecated key (it is invalid now),"
    "we can fix&enable this test again when we have some"
    "new pair in deprecated_keys list.",
)
def test_deprecated_keys_renamed(config):
    """Deprecated keys are renamed when defined on the top-level."""
    pc = PackageConfigSchema().load(config)
    assert pc.upstream_package_name == "upstream_package"
    assert pc.packages["package"].upstream_package_name == "upstream_package"


@pytest.mark.parametrize(
    "config",
    [
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "package.spec",
                "upstream_project_name": "upstream_package",
            },
            id="top_level",
        ),
        pytest.param(
            {
                "packages": {
                    "package": {
                        "specfile_path": "package.spec",
                        "upstream_project_name": "upstream_package",
                    },
                },
            },
            id="in_packages",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "packages.spec",
                "upstream_package_name": "package",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "pull_request",
                        "upstream_project_name": "upstream_package",
                    },
                ],
            },
            id="in_job",
        ),
        pytest.param(
            {
                "downstream_package_name": "package",
                "specfile_path": "packages.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "pull_request",
                        "packages": {
                            "package": {
                                "upstream_project_name": "upstream_package",
                            },
                        },
                    },
                ],
            },
            id="in_job_packages",
        ),
    ],
)
def test_deprecated_keys_invalid(config):
    """Old deprecated keys are now invalid."""
    with pytest.raises(ValidationError, match=r"upstream_project_name.+Unknown field"):
        PackageConfigSchema().load(config)


def test_loading_packageless_config():
    """Check that configuration data without any 'packages' key is correctly
    loaded."""
    config_data = {
        "downstream_package_name": "foo",
        "upstream_package_name": "foo",
        "issue_repository": "https://github.com/foo/bar",
        "actions": {
            "get-current-version": [
                "python3 setup.py --version",
            ],
        },
        "files_to_sync": ["packaging/foo.spec", "packit.yaml"],
        "srpm_build_deps": ["git", "python"],
        "specfile_path": "packaging/foo.spec",
        "jobs": [
            {
                "job": "copr_build",
                "trigger": "pull_request",
                "targets": ["fedora-stable", "epel-9"],
            },
            {
                "job": "copr_build",
                "trigger": "commit",
                "targets": ["fedora-stable", "epel-9"],
                "project": "foo-dev",
                "list_on_homepage": True,
                "preserve_project": True,
            },
        ],
    }
    loaded_config = PackageConfigSchema().load(config_data)

    # Prepare objects in the expected configuration
    top_level_config = {k: v for k, v in config_data.items() if k != "jobs"}
    top_level_config["files_to_sync"] = [
        SyncFilesItem(src=[item], dest=item)
        for item in top_level_config["files_to_sync"]
    ]
    top_level_config["actions"] = {
        ActionName(k): v for k, v in top_level_config["actions"].items()
    }
    job_config = [
        {
            f"_{k}" if k == "targets" else k: v
            for k, v in job.items()
            if k not in {"job", "trigger"}
        }
        for job in config_data["jobs"]
    ]
    expected_config = PackageConfig(
        packages={"foo": CommonPackageConfig(paths=["./"], **top_level_config)},
        jobs=[
            JobConfig(
                type=JobType.copr_build,
                trigger=JobConfigTriggerType.pull_request,
                packages={
                    "foo": CommonPackageConfig(
                        paths=["./"],
                        **(top_level_config | job_config[0]),
                    ),
                },
            ),
            JobConfig(
                type=JobType.copr_build,
                trigger=JobConfigTriggerType.commit,
                packages={
                    "foo": CommonPackageConfig(
                        paths=["./"],
                        **(top_level_config | job_config[1]),
                    ),
                },
            ),
        ],
    )
    assert loaded_config == expected_config


def test_package_naming():
    """Either the key from 'packages' or 'downstream_package_name' is used to name
    a package."""
    config1 = PackageConfigSchema().load(
        {
            "downstream_package_name": "baar",
            "specfile_path": "fedora/baar.spec",
        },
    )
    config2 = PackageConfigSchema().load(
        {
            "packages": {
                "baar": {
                    "specfile_path": "fedora/baar.spec",
                },
            },
        },
    )
    assert config1 == config2
    assert config1.downstream_package_name == config2.downstream_package_name == "baar"
    # check the default value for 'paths'
    assert config1.paths == config2.paths == ["./"]
    assert config1.packages["baar"].paths == config2.packages["baar"].paths == ["./"]


def test_multiple_packages():
    """A configuration with multiple packages can be loaded.
    Values can be accessed only through the 'packages' attribute."""
    config = {
        "packages": {
            "foo": {
                "specfile_path": "foo/foo.spec",
                "paths": ["foo"],
            },
            "baar": {
                "specfile_path": "baar/baar.spec",
                "paths": ["baar"],
            },
            "jeee": {
                "specfile_path": "jeee/jeee.spec",
                "paths": ["jeee"],
            },
        },
    }
    pc = PackageConfigSchema().load(config)
    assert pc.packages.keys() == pc.jobs[0].packages.keys() == config["packages"].keys()
    # Attributes not related to packages are accessible
    pc.packages = pc.packages
    pc.jobs = pc.jobs
    pc.jobs[0].type = pc.jobs[0].type
    pc.jobs[0].trigger = pc.jobs[0].trigger
    # Accessing package related attributes without 'packages' raises an error
    with pytest.raises(AttributeError, match="ambiguous to get"):
        _ = pc.jobs[0].enable_net
    with pytest.raises(AttributeError, match="ambiguous to get"):
        _ = pc.enable_net
    with pytest.raises(AttributeError, match="ambiguous to set"):
        pc.jobs[0].enable_net = False
    with pytest.raises(AttributeError, match="ambiguous to set"):
        pc.enable_net = False


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            {
                "downstream_package_name": "apple",
                "specfile_path": "apple.spec",
                "jobs": [
                    {"job": "copr_build", "trigger": "pull_request"},
                    {"job": "tests", "trigger": "pull_request"},
                ],
            },
            id="no_package_selected",
        ),
        pytest.param(
            {
                "downstream_package_name": "apple",
                "specfile_path": "apple.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "pull_request",
                        "packages": ["apple"],
                    },
                    {
                        "job": "tests",
                        "trigger": "pull_request",
                        "packages": {"apple": {}},
                    },
                ],
            },
            id="package_selected",
        ),
        pytest.param(
            {
                "downstream_package_name": "apple",
                "specfile_path": "apple.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "pull_request",
                        "packages": {"apple": {}},
                    },
                    {"job": "tests", "trigger": "pull_request", "packages": ["apple"]},
                ],
            },
            id="package_selected",
        ),
    ],
)
def test_selecting_packages_in_jobs(data):
    """Jobs can select to work with all or just a subset of the packages defined top-level"""
    expected_config = PackageConfig(
        packages={
            "apple": CommonPackageConfig(
                downstream_package_name="apple",
                specfile_path="apple.spec",
            ),
        },
        jobs=[
            JobConfig(
                type=JobType.copr_build,
                trigger=JobConfigTriggerType.pull_request,
                packages={
                    "apple": CommonPackageConfig(
                        downstream_package_name="apple",
                        specfile_path="apple.spec",
                    ),
                },
            ),
            JobConfig(
                type=JobType.tests,
                trigger=JobConfigTriggerType.pull_request,
                packages={
                    "apple": CommonPackageConfig(
                        downstream_package_name="apple",
                        specfile_path="apple.spec",
                    ),
                },
            ),
        ],
    )
    loaded_config = PackageConfigSchema().load(data)
    assert loaded_config == expected_config


@pytest.mark.parametrize(
    "data, error",
    [
        pytest.param(
            {
                "downstream_package_name": "apple",
                "specfile_path": "apple.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "pull_request",
                        "packages": "apple",
                    },
                ],
            },
            r"'str'.+instead of 'list' or 'dict'",
            id="package_is_str",
        ),
        pytest.param(
            {
                "downstream_package_name": "apple",
                "specfile_path": "apple.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "pull_request",
                        "packages": ["pear"],
                    },
                ],
            },
            r"Undefined.+: pear\.",
            id="package_is_not_present",
        ),
    ],
)
def test_package_error_in_job(data, error):
    """The 'packages' key in a job is of a wrong type, or references a
    packages which is not defined on the top-level 'packages' dict.
    """
    with pytest.raises(ValidationError, match=error):
        PackageConfigSchema().load(data)


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            {
                "packages": {
                    "apple": {
                        "specfile_path": "apple.spec",
                        "paths": ["apple"],
                    },
                    "pear": {
                        "specfile_path": "pear.spec",
                        "paths": ["pear"],
                    },
                },
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "pull_request",
                    },
                    {"job": "tests", "trigger": "pull_request", "packages": ["pear"]},
                ],
            },
            id="none_selected",
        ),
        pytest.param(
            {
                "packages": {
                    "apple": {
                        "specfile_path": "apple.spec",
                        "paths": ["apple"],
                    },
                    "pear": {
                        "specfile_path": "pear.spec",
                        "paths": ["pear"],
                    },
                },
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "pull_request",
                        "packages": ["pear", "apple"],
                    },
                    {"job": "tests", "trigger": "pull_request", "packages": ["pear"]},
                ],
            },
            id="multiple_selected",
        ),
    ],
)
def test_multiple_packages_in_jobs(data):
    """Check that it's possible to select one or more packages in jobs."""
    apple_config = CommonPackageConfig(
        downstream_package_name="apple",
        specfile_path="apple.spec",
        paths=["apple"],
    )
    pear_config = CommonPackageConfig(
        downstream_package_name="pear",
        specfile_path="pear.spec",
        paths=["pear"],
    )
    expected_config = PackageConfig(
        packages={
            "apple": apple_config,
            "pear": pear_config,
        },
        jobs=[
            JobConfig(
                type=JobType.copr_build,
                trigger=JobConfigTriggerType.pull_request,
                packages={
                    "apple": apple_config,
                    "pear": pear_config,
                },
            ),
            JobConfig(
                type=JobType.tests,
                trigger=JobConfigTriggerType.pull_request,
                packages={
                    "pear": pear_config,
                },
            ),
        ],
    )
    loaded_config = PackageConfigSchema().load(data)
    assert loaded_config == expected_config


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            {
                "specfile_path": "fedora/foo.spec",
                "packages": {
                    "foo": {},
                },
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "pull_request",
                        "specfile_path": "copr/foo.spec",
                    },
                ],
            },
            id="override_in_job",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/foo.spec",
                "downstream_package_name": "foo",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "pull_request",
                        "packages": {
                            "foo": {
                                "specfile_path": "copr/foo.spec",
                            },
                        },
                    },
                ],
            },
            id="override_in_job",
        ),
    ],
)
def test_configuring_packages_in_jobs(data):
    """Configuration of individual or all packages can be overwritten in jobs"""
    package_foo_config = CommonPackageConfig(
        downstream_package_name="foo",
        specfile_path="fedora/foo.spec",
    )
    job_foo_config = CommonPackageConfig(
        downstream_package_name="foo",
        specfile_path="copr/foo.spec",
    )
    expected_config = PackageConfig(
        packages={"foo": package_foo_config},
        jobs=[
            JobConfig(
                type=JobType.copr_build,
                trigger=JobConfigTriggerType.pull_request,
                packages={"foo": job_foo_config},
            ),
        ],
    )
    loaded_config = PackageConfigSchema().load(data)
    assert loaded_config == expected_config


def test_find_remote_package_config_no_commit():
    exception = GithubAPIException()
    exception.__cause__ = GithubException(404, None, None)

    project = flexmock()
    project.should_receive("get_files").and_raise(exception)

    assert find_remote_package_config(project, ref=None) is None


def test_find_remote_package_config_should_raise():
    exception = GithubAPIException()
    exception.__cause__ = GithubException(403, None, None)

    project = flexmock()
    project.should_receive("get_files").and_raise(exception)

    with pytest.raises(GithubAPIException):
        find_remote_package_config(project, ref=None)
