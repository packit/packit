from pathlib import Path
from typing import Optional

import pytest
from flexmock import flexmock
from marshmallow import ValidationError

from ogr.abstract import GitProject, GitService
from packit.actions import ActionName
from packit.config import (
    JobType,
    JobConfigTriggerType,
    JobConfig,
    get_package_config_from_repo,
    SyncFilesConfig,
)
from packit.config.job_config import JobMetadataConfig
from packit.config.package_config import (
    get_specfile_path_from_repo,
    PackageConfig,
    get_local_specfile_path,
)
from packit.schema import MM3, PackageConfigSchema
from packit.sync import SyncFilesItem
from tests.spellbook import UP_OSBUILD, SYNC_FILES
from tests.unit.test_config import (
    get_job_config_dict_full,
    get_job_config_dict_simple,
    get_job_config_simple,
    get_job_config_full,
    get_default_job_config,
    get_job_config_dict_build_for_branch,
    get_job_config_build_for_branch,
)


@pytest.fixture()
def job_config_simple():
    return get_job_config_simple()


@pytest.mark.parametrize(
    "files,expected", [(["foo.spec"], "foo.spec"), ([], None)],
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
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.pull_request,
                    )
                ],
            ),
            None,
        ),
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.pull_request,
                        metadata=JobMetadataConfig(project="example"),
                    )
                ],
            ),
            "example",
        ),
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.release,
                        metadata=JobMetadataConfig(project="example1"),
                    ),
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.pull_request,
                        metadata=JobMetadataConfig(project="example2"),
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


def test_package_config_equal(job_config_simple):
    assert PackageConfig(
        specfile_path="fedora/package.spec",
        synced_files=SyncFilesConfig(
            files_to_sync=[SyncFilesItem(src="packit.yaml", dest="packit.yaml")]
        ),
        jobs=[job_config_simple],
        downstream_package_name="package",
        create_pr=True,
    ) == PackageConfig(
        specfile_path="fedora/package.spec",
        synced_files=SyncFilesConfig(
            files_to_sync=[SyncFilesItem(src="packit.yaml", dest="packit.yaml")]
        ),
        jobs=[job_config_simple],
        downstream_package_name="package",
        create_pr=True,
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
            create_pr=False,
        ),
    ],
)
def test_package_config_not_equal(not_equal_package_config):
    config = PackageConfig(
        specfile_path="fedora/package.spec",
        synced_files=SyncFilesConfig(
            files_to_sync=[
                SyncFilesItem(src="c", dest="c"),
                SyncFilesItem(src="d", dest="d"),
            ]
        ),
        jobs=[get_job_config_full()],
        create_pr=True,
    )
    assert config != not_equal_package_config


@pytest.mark.parametrize(
    "raw,is_valid",
    [
        (
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": "fedora/foobar.spec",
            },
            False,
        ),
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
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "metadata": {"dist-git-branch": "fedora-all"},
                    }
                ],
            },
            True,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "metadata": {"dist_git_branches": ["fedora-all", "epel-8"]},
                    }
                ],
            },
            True,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "release",
                        "metadata": {"targets": "fedora-stable"},
                    }
                ],
            },
            True,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "copr_build",
                        "trigger": "release",
                        "metadata": {
                            "targets": ["fedora-stable", "fedora-development"]
                        },
                    }
                ],
            },
            True,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "metadata": {
                            "targets": ["f31", "f32"],
                            "timeout": 123,
                            "owner": "santa",
                            "project": "gifts",
                        },
                    }
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
        (
            {
                "specfile_path": "fedora/package.spec",
                "notifications": {"pull_request": {"successful_build": False}},
            },
            True,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "notifications": {"pull_request": {"successful_build": "nie"}},
            },
            False,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "notifications": {"pull_request": False},
            },
            False,
        ),
    ],
)
def test_package_config_validate(raw, is_valid):
    if not is_valid:
        with pytest.raises((ValidationError, ValueError)):
            PackageConfig.get_from_dict(raw)
    else:
        PackageConfig.get_from_dict(raw)


@pytest.mark.xfail(not MM3, reason="Marshmallow v2 doesn't raise when unknown field")
@pytest.mark.parametrize(
    "raw,is_valid",
    [
        (
            {
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "unknown": "key",
                    }
                ],
            },
            False,
        ),
        (
            {
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "metadata": {"unknown": "key"},
                    }
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
        }
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
                "synced_files": ["fedora/package.spec"],
                "jobs": [get_job_config_dict_full()],
                "downstream_package_name": "package",
                "create_pr": False,
            },
            PackageConfig(
                specfile_path="fedora/package.spec",
                downstream_package_name="package",
                create_pr=False,
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        )
                    ]
                ),
                jobs=[
                    get_job_config_full(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        create_pr=False,
                        synced_files=SyncFilesConfig(
                            files_to_sync=[
                                SyncFilesItem(
                                    src="fedora/package.spec",
                                    dest="fedora/package.spec",
                                )
                            ]
                        ),
                    )
                ],
            ),
            id="specfile_path+synced_files+job_config_full+downstream_package_name+create_pr",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": [
                    "fedora/package.spec",
                    "somefile",
                    "other",
                    "directory/files",
                ],
                "jobs": [get_job_config_dict_simple()],
                "downstream_package_name": "package",
            },
            PackageConfig(
                downstream_package_name="package",
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
                jobs=[
                    get_job_config_simple(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        synced_files=SyncFilesConfig(
                            files_to_sync=[
                                SyncFilesItem(
                                    src="fedora/package.spec",
                                    dest="fedora/package.spec",
                                ),
                                SyncFilesItem(src="somefile", dest="somefile"),
                                SyncFilesItem(src="other", dest="other"),
                                SyncFilesItem(
                                    src="directory/files", dest="directory/files"
                                ),
                            ]
                        ),
                    )
                ],
            ),
            id="specfile_path+synced_files+job_config_dict_simple+downstream_package_name",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/package.spec"],
                "jobs": [get_job_config_dict_full()],
                "downstream_package_name": "package",
            },
            PackageConfig(
                downstream_package_name="package",
                specfile_path="fedora/package.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        )
                    ]
                ),
                jobs=[
                    get_job_config_full(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        synced_files=SyncFilesConfig(
                            files_to_sync=[
                                SyncFilesItem(
                                    src="fedora/package.spec",
                                    dest="fedora/package.spec",
                                )
                            ]
                        ),
                    )
                ],
            ),
            id="specfile_path+synced_files(spec_only)+job_config_full+downstream_package_name",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/package.spec", "somefile"],
                "jobs": [get_job_config_dict_full()],
                "downstream_package_name": "package",
            },
            PackageConfig(
                downstream_package_name="package",
                specfile_path="fedora/package.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        ),
                        SyncFilesItem(src="somefile", dest="somefile"),
                    ]
                ),
                jobs=[
                    get_job_config_full(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        synced_files=SyncFilesConfig(
                            files_to_sync=[
                                SyncFilesItem(
                                    src="fedora/package.spec",
                                    dest="fedora/package.spec",
                                ),
                                SyncFilesItem(src="somefile", dest="somefile"),
                            ]
                        ),
                    )
                ],
            ),
            id="specfile_path+synced_files+job_config_full+downstream_package_name",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/package.spec"],
                "jobs": [get_job_config_dict_full()],
                "upstream_project_url": "https://github.com/asd/qwe",
                "upstream_package_name": "qwe",
                "dist_git_base_url": "https://something.wicked",
                "downstream_package_name": "package",
            },
            PackageConfig(
                downstream_package_name="package",
                specfile_path="fedora/package.spec",
                upstream_project_url="https://github.com/asd/qwe",
                upstream_package_name="qwe",
                dist_git_base_url="https://something.wicked",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        )
                    ]
                ),
                jobs=[
                    get_job_config_full(
                        downstream_package_name="package",
                        specfile_path="fedora/package.spec",
                        upstream_project_url="https://github.com/asd/qwe",
                        upstream_package_name="qwe",
                        dist_git_base_url="https://something.wicked",
                        synced_files=SyncFilesConfig(
                            files_to_sync=[
                                SyncFilesItem(
                                    src="fedora/package.spec",
                                    dest="fedora/package.spec",
                                )
                            ]
                        ),
                    )
                ],
            ),
            id="specfile_path+synced_files+job_config_dict_full+upstream_project_url"
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
                specfile_path="fedora/package.spec",
                actions={
                    ActionName.pre_sync: "some/pre-sync/command --option",
                    ActionName.get_current_version: "get-me-version",
                },
                jobs=[],
                upstream_project_url="https://github.com/asd/qwe",
                upstream_package_name="qwe",
                dist_git_base_url="https://something.wicked",
                downstream_package_name="package",
            ),
            id="specfile_path+actions+empty_jobs+upstream_project_url"
            "+upstream_package_name+dist_git_base_url+downstream_package_name",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["fedora/package.spec"],
                "downstream_package_name": "package",
            },
            PackageConfig(
                downstream_package_name="package",
                specfile_path="fedora/package.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[
                        SyncFilesItem(
                            src="fedora/package.spec", dest="fedora/package.spec"
                        )
                    ]
                ),
                jobs=get_default_job_config(
                    downstream_package_name="package",
                    specfile_path="fedora/package.spec",
                    synced_files=SyncFilesConfig(
                        files_to_sync=[
                            SyncFilesItem(
                                src="fedora/package.spec", dest="fedora/package.spec"
                            )
                        ]
                    ),
                ),
            ),
            id="specfile_path+synced_files+downstream_package_name",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "spec_source_id": 3,
                "jobs": [get_job_config_dict_build_for_branch()],
            },
            PackageConfig(
                specfile_path="fedora/package.spec",
                spec_source_id="Source3",
                jobs=[
                    get_job_config_build_for_branch(
                        specfile_path="fedora/package.spec", spec_source_id="Source3",
                    )
                ],
            ),
            id="specfile_path+get_job_config_dict_build_for_branch",
        ),
    ],
)
def test_package_config_parse(raw, expected):
    package_config = PackageConfig.get_from_dict(raw_dict=raw)
    assert package_config
    # tests for https://github.com/packit-service/packit-service/pull/342
    if expected.jobs:
        for j in package_config.jobs:
            assert j.type
    assert package_config == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "jobs": [
                    {
                        "job": "build",
                        "trigger": "release",
                        "specfile_path": "somewhere/package.spec",
                    }
                ],
            },
            PackageConfig(
                specfile_path="fedora/package.spec",
                jobs=[
                    JobConfig(
                        type=JobType.build,
                        trigger=JobConfigTriggerType.release,
                        specfile_path="somewhere/package.spec",
                    )
                ],
            ),
            id="override-specfile_path",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "synced_files": ["x", "y"],
                "actions": {"post-upstream-clone": "ls"},
                "spec_source_id": "Source0",
                "jobs": [
                    {
                        "job": "build",
                        "trigger": "release",
                        "specfile_path": "somewhere/package.spec",
                        "synced_files": ["a", "b", "c"],
                        "actions": {"create-archive": "ls"},
                        "spec_source_id": "Source1",
                    }
                ],
            },
            PackageConfig(
                specfile_path="fedora/package.spec",
                synced_files=SyncFilesConfig([SyncFilesItem(x, x) for x in ("x", "y")]),
                actions={ActionName.post_upstream_clone: "ls"},
                jobs=[
                    JobConfig(
                        type=JobType.build,
                        trigger=JobConfigTriggerType.release,
                        specfile_path="somewhere/package.spec",
                        synced_files=SyncFilesConfig(
                            [SyncFilesItem(x, x) for x in ("a", "b", "c")]
                        ),
                        actions={ActionName.create_archive: "ls"},
                        spec_source_id="Source1",
                    )
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
                "specfile_path": "fedora/package.spec",
                "jobs": [{"job": "build", "trigger": "release", "actions": ["a"]}],
            },
            "'dict' required, got <class 'list'>.",
            id="bad_actions",
        ),
        pytest.param(
            {
                "specfile_path": "fedora/package.spec",
                "jobs": [{"job": "build", "trigger": "release", "synced_files": "a"}],
            },
            "Invalid input type.",
            id="bad_synced_files",
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
                "synced_files": ["fedora/package.spec"],
                "jobs": [],
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
                downstream_package_name="package",
                upstream_package_name="package",
            ),
        )
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
        "synced_files": ["fedora/foobar.spec"],
        "specfile_path": "fedora/package.spec",
        "create_pr": False,
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
        create_pr=False,
        jobs=get_default_job_config(
            dist_git_base_url="https://packit.dev/",
            downstream_package_name="packit",
            dist_git_namespace="awesome",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="fedora/foobar.spec", dest="fedora/foobar.spec")
                ]
            ),
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
    "content,project,mock_spec_search,spec_path_option,spec_path",
    [
        (
            "synced_files:\n"
            "  - packit.spec\n"
            "  - src: .packit.yaml\n"
            "    dest: .packit2.yaml",
            GitProject(repo="", service=GitService(), namespace=""),
            True,
            None,
            "packit.spec",
        ),
        (
            "synced_files:\n"
            "  - packit.spec\n"
            "  - src: .packit.yaml\n"
            "    dest: .packit2.yaml",
            GitProject(repo="", service=GitService(), namespace=""),
            False,
            "packit.spec",
            "packit.spec",
        ),
    ],
)
def test_get_package_config_from_repo(
    content,
    project: GitProject,
    mock_spec_search: bool,
    spec_path: Optional[str],
    spec_path_option: Optional[str],
):
    gp = flexmock(GitProject)
    gp.should_receive("full_repo_name").and_return("a/b")
    gp.should_receive("get_file_content").and_return(content)
    if mock_spec_search:
        gp.should_receive("get_files").and_return(["packit.spec"]).once()
    config = get_package_config_from_repo(
        project=project, ref="", spec_file_path=spec_path_option
    )
    assert isinstance(config, PackageConfig)
    assert config.specfile_path == spec_path
    assert config.synced_files == SyncFilesConfig(
        files_to_sync=[
            SyncFilesItem(src="packit.spec", dest="packit.spec"),
            SyncFilesItem(src=".packit.yaml", dest=".packit2.yaml"),
        ]
    )
    assert config.create_pr


@pytest.mark.parametrize("content", ["{}"])
def test_get_package_config_from_repo_spec_file_not_defined(content):
    gp = flexmock(GitProject)
    gp.should_receive("full_repo_name").and_return("a/b")
    gp.should_receive("get_file_content").and_return(content)
    gp.should_receive("get_files").and_return(["packit.spec"])
    git_project = GitProject(repo="", service=GitService(), namespace="")
    config = get_package_config_from_repo(project=git_project, ref="")
    assert isinstance(config, PackageConfig)
    assert Path(config.specfile_path).name == "packit.spec"
    assert config.create_pr


@pytest.mark.parametrize(
    "package_config, all_synced_files",
    [
        (
            PackageConfig(
                config_file_path="packit.yaml",
                specfile_path="file.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[SyncFilesItem(src="file.spec", dest="file.spec")]
                ),
            ),
            SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="file.spec", dest="file.spec"),
                    SyncFilesItem(src="packit.yaml", dest="packit.yaml"),
                ]
            ),
        ),
        (
            PackageConfig(
                config_file_path="packit.yaml",
                specfile_path="file.spec",
                synced_files=SyncFilesConfig(
                    files_to_sync=[SyncFilesItem(src="file.txt", dest="file.txt")]
                ),
            ),
            SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="file.txt", dest="file.txt"),
                    SyncFilesItem(src="file.spec", dest="file.spec"),
                    SyncFilesItem(src="packit.yaml", dest="packit.yaml"),
                ]
            ),
        ),
        (
            PackageConfig(
                config_file_path="packit.yaml",
                specfile_path="file.spec",
                synced_files=SyncFilesConfig([]),
            ),
            SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="file.spec", dest="file.spec"),
                    SyncFilesItem(src="packit.yaml", dest="packit.yaml"),
                ]
            ),
        ),
    ],
)
def test_get_all_files_to_sync(package_config, all_synced_files):
    assert package_config.get_all_files_to_sync() == all_synced_files


def test_notifications_section():
    pc = PackageConfig.get_from_dict({"specfile_path": "package.spec"})
    assert pc.notifications.pull_request.successful_build


def test_get_local_specfile_path():
    assert str(get_local_specfile_path(UP_OSBUILD)) == "osbuild.spec"
    assert not get_local_specfile_path(SYNC_FILES)


@pytest.mark.parametrize(
    "package_config",
    [
        PackageConfig(
            specfile_path="fedora/package.spec",
            downstream_package_name="package",
            upstream_package_name="package",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="fedora/package.spec", dest="fedora/package.spec")
                ]
            ),
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            downstream_package_name="package",
            synced_files=SyncFilesConfig(
                files_to_sync=[
                    SyncFilesItem(src="fedora/package.spec", dest="fedora/package.spec")
                ]
            ),
            jobs=[
                get_job_config_full(
                    specfile_path="fedora/package.spec",
                    downstream_package_name="package",
                    synced_files=SyncFilesConfig(
                        files_to_sync=[
                            SyncFilesItem(
                                src="fedora/package.spec", dest="fedora/package.spec"
                            )
                        ]
                    ),
                )
            ],
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            actions={
                ActionName.pre_sync: "some/pre-sync/command --option",
                ActionName.get_current_version: "get-me-version",
            },
            jobs=[],
            upstream_project_url="https://github.com/asd/qwe",
            upstream_package_name="qwe",
            dist_git_base_url="https://something.wicked",
            downstream_package_name="package",
            spec_source_id="Source1",
        ),
    ],
)
def test_serialize_and_deserialize(package_config):
    schema = PackageConfigSchema()
    serialized = schema.dump_config(package_config)
    new_package_config = schema.load_config(serialized)
    assert package_config == new_package_config
