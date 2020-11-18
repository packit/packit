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
from packit.config.job_config import JobMetadataConfig
from packit.schema import JobConfigSchema


def get_job_config_dict_simple(**update):
    result = {"job": "build", "trigger": "release"}
    result.update(update)
    return result


def get_job_config_simple(**kwargs):
    """ pass kwargs to JobConfig constructor """
    return JobConfig(type=JobType.build, trigger=JobConfigTriggerType.release, **kwargs)


@pytest.fixture()
def job_config_simple():
    return get_job_config_simple()


def get_job_config_dict_full():
    return {
        "job": "propose_downstream",
        "trigger": "pull_request",
        "metadata": {"dist-git-branch": "master"},
    }


def get_job_config_full(**kwargs):
    """ pass kwargs to JobConfig constructor """
    return JobConfig(
        type=JobType.propose_downstream,
        trigger=JobConfigTriggerType.pull_request,
        metadata=JobMetadataConfig(dist_git_branches=["master"]),
        **kwargs
    )


@pytest.fixture()
def job_config_full():
    return get_job_config_full()


def get_job_config_dict_build_for_branch():
    return {
        "job": "copr_build",
        "trigger": "commit",
        "metadata": {"branch": "build-branch", "scratch": True},
    }


def get_job_config_build_for_branch(**kwargs):
    """ pass kwargs to JobConfig constructor """
    return JobConfig(
        type=JobType.copr_build,
        trigger=JobConfigTriggerType.commit,
        metadata=JobMetadataConfig(branch="build-branch", scratch=True),
        **kwargs
    )


def get_default_job_config(**kwargs):
    """ pass kwargs to JobConfig constructor """
    return [
        JobConfig(
            type=JobType.copr_build,
            trigger=JobConfigTriggerType.pull_request,
            metadata=JobMetadataConfig(targets=["fedora-stable"]),
            **kwargs
        ),
        JobConfig(
            type=JobType.tests,
            trigger=JobConfigTriggerType.pull_request,
            metadata=JobMetadataConfig(targets=["fedora-stable"]),
            **kwargs
        ),
        JobConfig(
            type=JobType.propose_downstream,
            trigger=JobConfigTriggerType.release,
            metadata=JobMetadataConfig(dist_git_branches=["fedora-all"]),
            **kwargs
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
            get_job_config_simple(metadata=JobMetadataConfig(preserve_project=False)),
        ),
        (
            get_job_config_dict_simple(metadata={"preserve_project": False}),
            get_job_config_simple(metadata=JobMetadataConfig(preserve_project=False)),
        ),
        (
            get_job_config_dict_simple(metadata={"preserve_project": True}),
            get_job_config_simple(metadata=JobMetadataConfig(preserve_project=True)),
        ),
    ],
)
def test_job_config_parse(raw, expected_config):
    job_config = JobConfig.get_from_dict(raw_dict=raw)
    assert job_config == expected_config


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
    serialized = schema.dump_config(config)
    new_config = schema.load_config(serialized)
    assert new_config == config
