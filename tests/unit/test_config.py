# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import os

import pytest
from flexmock import flexmock
from marshmallow import ValidationError
from ogr import GithubService, PagureService

from packit.config import (
    Config,
    JobConfig,
    JobType,
    JobConfigTriggerType,
)
from packit.config.aliases import DEFAULT_VERSION
from packit.schema import JobConfigSchema, JobMetadataSchema


def get_job_config_dict_simple(**update):
    result = {"job": "build", "trigger": "release"}
    result.update(update)
    return result


def get_job_config_simple(**kwargs):
    """pass kwargs to JobConfig constructor"""
    return JobConfig(type=JobType.build, trigger=JobConfigTriggerType.release, **kwargs)


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
    return JobConfig(
        type=JobType.propose_downstream,
        trigger=JobConfigTriggerType.pull_request,
        dist_git_branches=["master"],
        **kwargs,
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
    return JobConfig(
        type=JobType.copr_build,
        trigger=JobConfigTriggerType.commit,
        branch="build-branch",
        scratch=True,
        **kwargs,
    )


def get_default_job_config(**kwargs):
    """pass kwargs to JobConfig constructor"""
    return [
        JobConfig(
            type=JobType.copr_build,
            trigger=JobConfigTriggerType.pull_request,
            _targets=[DEFAULT_VERSION],
            **kwargs,
        ),
        JobConfig(
            type=JobType.tests,
            trigger=JobConfigTriggerType.pull_request,
            _targets=[DEFAULT_VERSION],
            **kwargs,
        ),
        JobConfig(
            type=JobType.propose_downstream,
            trigger=JobConfigTriggerType.release,
            dist_git_branches=["fedora-all"],
            **kwargs,
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
        JobConfig.get_from_dict(raw)
    else:
        with pytest.raises(ValidationError):
            JobConfig.get_from_dict(raw)


@pytest.mark.parametrize(
    "raw,expected_config",
    [
        (get_job_config_dict_simple(), get_job_config_simple()),
        (get_job_config_dict_full(), get_job_config_full()),
        (
            get_job_config_dict_simple(),
            get_job_config_simple(preserve_project=False),
        ),
        (
            get_job_config_dict_simple(preserve_project=False),
            get_job_config_simple(preserve_project=False),
        ),
        (
            get_job_config_dict_simple(preserve_project=True),
            get_job_config_simple(preserve_project=True),
        ),
    ],
)
def test_job_config_parse(raw, expected_config):
    job_config = JobConfig.get_from_dict(raw_dict=raw)
    assert job_config == expected_config


@pytest.mark.parametrize(
    "raw,expected,allowed_pr_authors,allowed_committers",
    [
        pytest.param(
            {
                "job": "koji_build",
                "trigger": "commit",
            },
            JobConfig(
                type=JobType.koji_build,
                trigger=JobConfigTriggerType.commit,
            ),
            ["packit"],
            [],
        ),
        pytest.param(
            {
                "job": "koji_build",
                "trigger": "commit",
                "allowed_committers": ["me"],
            },
            JobConfig(
                type=JobType.koji_build,
                trigger=JobConfigTriggerType.commit,
                allowed_committers=["me"],
            ),
            ["packit"],
            ["me"],
        ),
        pytest.param(
            {
                "job": "koji_build",
                "trigger": "commit",
                "allowed_committers": ["me"],
                "allowed_pr_authors": [],
            },
            JobConfig(
                type=JobType.koji_build,
                trigger=JobConfigTriggerType.commit,
                allowed_committers=["me"],
                allowed_pr_authors=[],
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


def test_get_user_config(tmp_path):
    user_config_file_path = tmp_path / ".packit.yaml"
    user_config_file_path.write_text(
        "---\n"
        "debug: true\n"
        "fas_user: rambo\n"
        "keytab_path: './rambo.keytab'\n"
        "kerberos_realm: STG.FEDORAPROJECT.ORG\n"
        "github_token: GITHUB_TOKEN\n"
        "pagure_user_token: PAGURE_TOKEN\n"
    )
    flexmock(os).should_receive("getenv").with_args("XDG_CONFIG_HOME").and_return(
        str(tmp_path)
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
        '        instance_url: "https://my.pagure.org"\n'
    )
    flexmock(os).should_receive("getenv").with_args("XDG_CONFIG_HOME").and_return(
        str(tmp_path)
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
        "---\n" "pagure_fork_token: yes-is-true-in-yaml-are-you-kidding-me?\n"
    )
    flexmock(os).should_receive("getenv").with_args("XDG_CONFIG_HOME").and_return(
        str(tmp_path)
    )
    Config.get_user_config()
    w = recwarn.pop(UserWarning)
    assert "pagure_fork_token" in str(w.message)


@pytest.mark.parametrize(
    "config",
    [get_job_config_simple(), get_job_config_full()],
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
                "job": "build",
                "trigger": "release",
                "enable_net": False,
                "metadata": {"branch": "main"},
            },
            {
                "job": "build",
                "trigger": "release",
                "enable_net": False,
                "branch": "main",
            },
            True,
        ),
        (
            {
                "job": "build",
                "trigger": "release",
                "metadata": {"enable_net": False, "branch": "main"},
            },
            {
                "job": "build",
                "trigger": "release",
                "enable_net": False,
                "branch": "main",
            },
            False,
        ),
        (
            {
                "job": "build",
                "trigger": "release",
                "enable_net": False,
                "branch": "main",
            },
            {
                "job": "build",
                "trigger": "release",
                "enable_net": False,
                "branch": "main",
            },
            False,
        ),
    ],
)
def test_deserialize_and_serialize_job_config(config_in, config_out, validation_error):
    schema = JobConfigSchema()
    if validation_error:
        with pytest.raises(ValidationError):
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
