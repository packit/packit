# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import os

import pytest
from flexmock import flexmock
from marshmallow import ValidationError
from ogr import GithubService, PagureService

from packit.config import (
    CommonPackageConfig,
    Config,
    JobConfig,
    JobConfigTriggerType,
    JobConfigView,
    JobType,
    PackageConfig,
)
from packit.config.aliases import DEFAULT_VERSION
from packit.schema import JobConfigSchema, JobMetadataSchema


def get_job_config_dict_simple(**update):
    result = {
        "job": "copr_build",
        "trigger": "release",
    }
    result.update(update)
    return result


def get_job_config_simple(**kwargs):
    """pass kwargs to JobConfig constructor"""
    package_name = kwargs.get("downstream_package_name", "package")
    return JobConfig(
        type=JobType.copr_build,
        trigger=JobConfigTriggerType.release,
        packages={package_name: CommonPackageConfig(**kwargs)},
    )


@pytest.fixture()
def job_config_simple():
    return get_job_config_simple()


def get_job_config_dict_full():
    return {
        "job": "propose_downstream",
        "trigger": "pull_request",
        "dist_git_branches": ["master"],
    }


def get_job_config_full(**kwargs):
    """pass kwargs to JobConfig constructor"""
    package_name = kwargs.get("downstream_package_name", "package")
    return JobConfig(
        type=JobType.propose_downstream,
        trigger=JobConfigTriggerType.pull_request,
        packages={
            package_name: CommonPackageConfig(dist_git_branches=["master"], **kwargs),
        },
    )


@pytest.fixture()
def job_config_full():
    return get_job_config_full()


def get_job_config_dict_build_for_branch():
    return {
        "job": "copr_build",
        "trigger": "commit",
        "branch": "build-branch",
        "scratch": True,
    }


def get_job_config_build_for_branch(**kwargs):
    """pass kwargs to JobConfig constructor"""
    package_name = kwargs.get("downstream_package_name", "package")
    return JobConfig(
        type=JobType.copr_build,
        trigger=JobConfigTriggerType.commit,
        packages={
            package_name: CommonPackageConfig(
                branch="build-branch",
                scratch=True,
                **kwargs,
            ),
        },
    )


def get_default_job_config(**kwargs):
    """pass kwargs to JobConfig constructor"""
    package_name = kwargs.get("downstream_package_name", "package")
    return [
        JobConfig(
            type=JobType.copr_build,
            trigger=JobConfigTriggerType.pull_request,
            packages={
                package_name: CommonPackageConfig(_targets=[DEFAULT_VERSION], **kwargs),
            },
        ),
        JobConfig(
            type=JobType.tests,
            trigger=JobConfigTriggerType.pull_request,
            packages={
                package_name: CommonPackageConfig(_targets=[DEFAULT_VERSION], **kwargs),
            },
        ),
        JobConfig(
            type=JobType.propose_downstream,
            trigger=JobConfigTriggerType.release,
            packages={
                package_name: CommonPackageConfig(
                    dist_git_branches=["fedora-all"],
                    **kwargs,
                ),
            },
        ),
    ]


def test_job_config_equal(job_config_simple):
    assert job_config_simple == job_config_simple


def test_job_config_not_equal(job_config_simple, job_config_full):
    assert job_config_simple != job_config_full


def test_job_config_blah():
    with pytest.raises(ValidationError) as ex:
        JobConfig.get_from_dict({"job": "asdqwe", "trigger": "salt"})
    assert "'trigger': ['Invalid enum member salt']" in str(ex.value)
    assert "'job': ['Invalid enum member asdqwe']" in str(ex.value)


def expanded_job_config_dict(**kwargs):
    config = {
        "job": "copr_build",
        "trigger": "pull_request",
        "packages": {"package": {"specfile_path": "package.spec"}},
    }
    config["packages"]["package"].update(**kwargs)
    return config


def expanded_job_config_object(**kwargs):
    package_config = {"specfile_path": "package.spec"}
    package_config.update(**kwargs)
    return JobConfig(
        type=JobType.copr_build,
        trigger=JobConfigTriggerType.pull_request,
        packages={"package": CommonPackageConfig(**package_config)},
    )


@pytest.mark.parametrize(
    "raw,is_valid",
    [
        ({}, False),
        ({"trigger": "release"}, False),
        ({"release_to": ["f28"]}, False),
        (expanded_job_config_dict(), True),
        (expanded_job_config_dict(dist_git_branches=["main"]), True),
    ],
)
def test_job_config_validate(raw, is_valid):
    if is_valid:
        JobConfig.get_from_dict(raw)
    else:
        with pytest.raises(ValidationError):
            JobConfig.get_from_dict(raw)


@pytest.mark.parametrize(
    "raw,expected_config",
    [
        (expanded_job_config_dict(), expanded_job_config_object()),
        (
            expanded_job_config_dict(dist_git_branches=["main"]),
            expanded_job_config_object(dist_git_branches=["main"]),
        ),
        (
            expanded_job_config_dict(),
            expanded_job_config_object(preserve_project=False),
        ),
        (
            expanded_job_config_dict(preserve_project=False),
            expanded_job_config_object(preserve_project=False),
        ),
        (
            expanded_job_config_dict(preserve_project=True),
            expanded_job_config_object(preserve_project=True),
        ),
    ],
)
def test_job_config_parse(raw, expected_config):
    job_config = JobConfig.get_from_dict(raw_dict=raw)
    assert job_config == expected_config


def test_deserialize_job_config_view():
    job_config = JobConfig(
        type=JobType.copr_build,
        trigger=JobConfigTriggerType.commit,
        packages={
            "a": CommonPackageConfig(specfile_path="a.spec"),
            "b": CommonPackageConfig(specfile_path="b.spec"),
        },
    )

    job_config_view = JobConfigView(job_config, "a")
    assert job_config_view.identifier == "a"
    dump = JobConfigSchema().dump(job_config_view)
    job_config_view_deserialization = JobConfig.get_from_dict(dump)
    assert isinstance(job_config_view_deserialization, JobConfigView)
    assert job_config_view.identifier == "a"


@pytest.mark.parametrize(
    "raw,expected,allowed_pr_authors,allowed_committers",
    [
        pytest.param(
            {
                "job": "koji_build",
                "trigger": "commit",
                "packages": {"package": {"specfile_path": "package.spec"}},
            },
            JobConfig(
                type=JobType.koji_build,
                trigger=JobConfigTriggerType.commit,
                packages={"package": CommonPackageConfig(specfile_path="package.spec")},
            ),
            ["packit"],
            [],
        ),
        pytest.param(
            {
                "job": "koji_build",
                "trigger": "commit",
                "packages": {
                    "package": {
                        "specfile_path": "package.spec",
                        "allowed_committers": ["me"],
                    },
                },
            },
            JobConfig(
                type=JobType.koji_build,
                trigger=JobConfigTriggerType.commit,
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="package.spec",
                        allowed_committers=["me"],
                    ),
                },
            ),
            ["packit"],
            ["me"],
        ),
        pytest.param(
            {
                "job": "koji_build",
                "trigger": "commit",
                "packages": {
                    "package": {
                        "specfile_path": "package.spec",
                        "allowed_committers": ["me"],
                        "allowed_pr_authors": [],
                    },
                },
            },
            JobConfig(
                type=JobType.koji_build,
                trigger=JobConfigTriggerType.commit,
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="package.spec",
                        allowed_committers=["me"],
                        allowed_pr_authors=[],
                    ),
                },
            ),
            [],
            ["me"],
        ),
    ],
)
def test_koji_build_allowlist(raw, expected, allowed_pr_authors, allowed_committers):
    job_config = JobConfig.get_from_dict(raw_dict=raw)
    assert job_config == expected
    assert job_config.allowed_pr_authors == allowed_pr_authors
    assert job_config.allowed_committers == allowed_committers


@pytest.mark.parametrize(
    "raw,expected,allowed_builders",
    [
        pytest.param(
            {
                "job": "bodhi_update",
                "trigger": "commit",
                "packages": {
                    "package": {
                        "specfile_path": "package.spec",
                    },
                },
            },
            JobConfig(
                type=JobType.bodhi_update,
                trigger=JobConfigTriggerType.commit,
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="package.spec",
                        allowed_builders=["packit"],
                    ),
                },
            ),
            ["packit"],
        ),
        pytest.param(
            {
                "job": "bodhi_update",
                "trigger": "commit",
                "packages": {
                    "package": {
                        "specfile_path": "package.spec",
                        "allowed_builders": ["me"],
                    },
                },
            },
            JobConfig(
                type=JobType.bodhi_update,
                trigger=JobConfigTriggerType.commit,
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="package.spec",
                        allowed_builders=["me"],
                    ),
                },
            ),
            ["me"],
        ),
    ],
)
def test_bodhi_updates_allowed(raw, expected, allowed_builders):
    job_config = JobConfig.get_from_dict(raw_dict=raw)
    assert job_config == expected
    assert job_config.allowed_builders == allowed_builders


@pytest.mark.parametrize(
    "raw,expected_packages_keys,identifiers",
    [
        pytest.param(
            {
                "upstream_project_url": "https://github.com/namespace/package",
                "packages": {
                    "package_a": {
                        "downstream_package_name": "package_a",
                        "paths": ["."],
                        "specfile_path": "package_a.spec",
                        "files_to_sync": ["package_a.spec", ".packit.yaml"],
                        "upstream_package_name": "package",
                    },
                    "package_b": {
                        "downstream_package_name": "package_b",
                        "identifier": "identifier_for_package_b",
                        "paths": ["."],
                        "specfile_path": "package_b.spec",
                        "files_to_sync": ["package_b.spec", ".packit.yaml"],
                        "upstream_package_name": "package",
                    },
                    "package_c": {
                        "downstream_package_name": "package_c",
                        "paths": ["."],
                        "specfile_path": "package_c.spec",
                        "files_to_sync": ["package_c.spec", ".packit.yaml"],
                        "upstream_package_name": "package_c",
                    },
                },
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "packages": {
                            "package_a": {"specfile_path": "a/package.spec"},
                            "package_b": {"specfile_path": "b/package.spec"},
                        },
                    },
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "packages": {
                            "package_c": {"specfile_path": "c/package.spec"},
                        },
                    },
                ],
            },
            [
                ["package_a"],
                ["package_b"],
                ["package_c"],
            ],
            ["package_a", "identifier_for_package_b", "package_c"],
        ),
        pytest.param(
            {
                "upstream_project_url": "https://github.com/namespace/package",
                "packages": {
                    "package_a": {
                        "downstream_package_name": "package_a",
                        "paths": ["."],
                        "specfile_path": "package_a.spec",
                        "files_to_sync": ["package_a.spec", ".packit.yaml"],
                        "upstream_package_name": "package",
                    },
                },
                "jobs": [
                    {
                        "job": "propose_downstream",
                        "trigger": "release",
                        "packages": {
                            "package_a": {"specfile_path": "a/package.spec"},
                        },
                    },
                ],
            },
            [
                ["package_a"],
            ],
            [None],
        ),
    ],
)
def test_job_config_views(raw, expected_packages_keys, identifiers):
    pkg_config = PackageConfig.get_from_dict(raw_dict=raw)
    job_views = pkg_config.get_job_views()
    for job_config_view, keys, identifier in zip(
        job_views,
        expected_packages_keys,
        identifiers,
    ):
        assert job_config_view.identifier == identifier
        assert set(job_config_view.packages.keys()) == set(keys)
        assert pkg_config.get_package_config_for(job_config_view)


def test_get_user_config(tmp_path):
    user_config_file_path = tmp_path / ".packit.yaml"
    user_config_file_path.write_text(
        "---\n"
        "debug: true\n"
        "fas_user: rambo\n"
        "keytab_path: './rambo.keytab'\n"
        "kerberos_realm: STG.FEDORAPROJECT.ORG\n"
        "github_token: GITHUB_TOKEN\n"
        "pagure_user_token: PAGURE_TOKEN\n",
    )
    flexmock(os).should_receive("getenv").with_args("XDG_CONFIG_HOME").and_return(
        str(tmp_path),
    )
    config = Config.get_user_config()
    assert config.debug and isinstance(config.debug, bool)
    assert config.fas_user == "rambo"
    assert config.keytab_path == "./rambo.keytab"
    assert config.kerberos_realm == "STG.FEDORAPROJECT.ORG"
    assert config.pkg_tool == "fedpkg"

    assert GithubService(token="GITHUB_TOKEN") in config.services
    assert PagureService(token="PAGURE_TOKEN") in config.services


def test_get_user_config_new_authentication(tmp_path):
    user_config_file_path = tmp_path / ".packit.yaml"
    user_config_file_path.write_text(
        "---\n"
        "debug: true\n"
        "fas_user: rambo\n"
        "keytab_path: './rambo.keytab'\n"
        "authentication:\n"
        "    github.com:\n"
        "        token: GITHUB_TOKEN\n"
        "    pagure:\n"
        "        token: PAGURE_TOKEN\n"
        '        instance_url: "https://my.pagure.org"\n',
    )
    flexmock(os).should_receive("getenv").with_args("XDG_CONFIG_HOME").and_return(
        str(tmp_path),
    )
    config = Config.get_user_config()
    assert config.debug and isinstance(config.debug, bool)
    assert config.fas_user == "rambo"
    assert config.keytab_path == "./rambo.keytab"
    assert config.kerberos_realm == "FEDORAPROJECT.ORG"

    assert GithubService(token="GITHUB_TOKEN") in config.services
    assert (
        PagureService(token="PAGURE_TOKEN", instance_url="https://my.pagure.org")
        in config.services
    )


def test_user_config_fork_token(tmp_path, recwarn):
    user_config_file_path = tmp_path / ".packit.yaml"
    user_config_file_path.write_text(
        "---\n" "pagure_fork_token: yes-is-true-in-yaml-are-you-kidding-me?\n",
    )
    flexmock(os).should_receive("getenv").with_args("XDG_CONFIG_HOME").and_return(
        str(tmp_path),
    )
    Config.get_user_config()
    w = recwarn.pop(UserWarning)
    assert "pagure_fork_token" in str(w.message)


@pytest.mark.parametrize(
    "config",
    [
        expanded_job_config_object(),
        expanded_job_config_object(dist_git_branches=["main"]),
    ],
)
def test_serialize_and_deserialize_job_config(config):
    schema = JobConfigSchema()
    serialized = schema.dump(config)
    new_config = schema.load(serialized)
    assert new_config == config


@pytest.mark.parametrize(
    "config_in,config_out,validation_error",
    [
        (
            {
                "job": "copr_build",
                "trigger": "release",
                "packages": {
                    "package": {
                        "specfile_path": "packages.spec",
                        "enable_net": False,
                        "branch": "main",
                    },
                },
            },
            {
                "job": "copr_build",
                "trigger": "release",
                "packages": {
                    "package": {
                        "specfile_path": "packages.spec",
                        "enable_net": False,
                        "branch": "main",
                    },
                },
            },
            False,
        ),
        (
            {
                "job": "copr_build",
                "trigger": "release",
                "packages": {
                    "package": {
                        "specfile_path": "packages.spec",
                        "enable_net": False,
                        "branch": "main",
                    },
                },
            },
            {
                "job": "copr_build",
                "trigger": "release",
                "packages": {
                    "package": {
                        "specfile_path": "packages.spec",
                        "enable_net": False,
                        "branch": "main",
                    },
                },
            },
            False,
        ),
        (
            {
                "job": "copr_build",
                "trigger": "release",
                "packages": {
                    "package": {
                        "specfile_path": "packages.spec",
                        "enable_net": False,
                        "branch": "main",
                    },
                },
            },
            {
                "job": "copr_build",
                "trigger": "release",
                "packages": {
                    "package": {
                        "specfile_path": "packages.spec",
                        "enable_net": False,
                        "branch": "main",
                    },
                },
            },
            False,
        ),
        (
            {
                "job": "tests",
                "trigger": "pull_request",
                "labels": ["regression", "long"],
                "packages": {
                    "package": {
                        "specfile_path": "packages.spec",
                        "enable_net": False,
                        "branch": "main",
                    },
                },
            },
            {
                "job": "tests",
                "trigger": "pull_request",
                "labels": ["regression", "long"],
                "packages": {
                    "package": {
                        "specfile_path": "packages.spec",
                        "enable_net": False,
                        "branch": "main",
                    },
                },
            },
            False,
        ),
        (
            {
                "job": "tests",
                "trigger": "ignore",
                "labels": ["regression", "long"],
                "packages": {
                    "package": {
                        "specfile_path": "packages.spec",
                        "enable_net": False,
                        "branch": "main",
                    },
                },
            },
            {
                "job": "tests",
                "trigger": "ignore",
                "labels": ["regression", "long"],
                "packages": {
                    "package": {
                        "specfile_path": "packages.spec",
                        "enable_net": False,
                        "branch": "main",
                    },
                },
            },
            False,
        ),
    ],
)
def test_deserialize_and_serialize_job_config(config_in, config_out, validation_error):
    schema = JobConfigSchema()
    if validation_error:
        with pytest.raises(ValidationError, match=validation_error):
            schema.dump(schema.load(config_in))
    else:
        serialized_from_in = schema.dump(schema.load(config_in))
        serialized_from_out = schema.dump(schema.load(config_out))
        assert serialized_from_in == serialized_from_out


@pytest.mark.parametrize(
    "config,is_valid",
    [
        ({}, True),
        ({"targets": []}, True),
        ({"targets": {}}, True),
        ({"targets": ["this", "is", "list"]}, True),
        ({"targets": {"a": {}, "b": {"distros": ["rhel-7"]}}}, True),
        ({"targets": {"a": {}, "b": {"additional_modules": ""}}}, True),
        (
            {
                "targets": {
                    "a": {},
                    "b": {
                        "additional_modules": "asd:1.2",
                        "additional_repos": ["http://foo.bar/"],
                    },
                },
            },
            True,
        ),
        (
            {"targets": {"b": {"additional_modules": None, "additional_repos": False}}},
            False,
        ),
        ({"targets": {"a": {}, "b": {"unknown": ["rhel-7"]}}}, False),
        ({"targets": {"a": {}, "b": {"distros": "not a list"}}}, False),
        ({"targets": {"this", "is", "set"}}, False),
    ],
)
def test_job_metadata_targets(config, is_valid):
    if is_valid:
        JobMetadataSchema().load(config)
    else:
        with pytest.raises(ValidationError):
            JobMetadataSchema().load(config)
