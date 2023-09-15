# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import json

import pytest
from click.testing import CliRunner
from flexmock import flexmock

from packit.api import PackitAPI
from packit.cli.builds import koji_build
from packit.cli.packit_base import packit_base
from packit.config import (
    package_config,
)
from packit.distgit import DistGit
from packit.local_project import LocalProject

DEFAULT_CONFIG_YAML = """
    {
        "specfile_path": "python-teamcity-messages.spec",
        "files_to_sync": ["python-teamcity-messages.spec", ".packit.yaml"],
        "upstream_package_name": "teamcity-messages",
        "downstream_package_name": "python-teamcity-messages",
        "upstream_project_url": "https://github.com/majamassarini/teamcity-messages",
        "upstream_tag_template": "v{version}",
        "jobs": [
            {
                "job": "copr_build",
                "trigger": "commit",
                "targets": ["fedora-rawhide", "fedora-stable"]
            },
            {
                "job": "propose_downstream",
                "trigger": "release",
                "dist_git_branches": ["fedora-rawhide", "fedora-stable"]
            },
            {
                "job": "koji_build",
                "trigger": "commit",
                "allowed_pr_authors": ["packit"],
                "dist_git_branches": ["fedora-rawhide", "fedora-stable"]
            },
            {
                "job": "bodhi_update",
                "trigger": "commit",
                "dist_git_branches": ["fedora-rawhide", "fedora-stable"]
            }
        ]
    }
    """


MONOREPO_CONFIG_YAML = """
    {
        "upstream_project_url": "https://github.com/majamassarini/teamcity-messages",
        "packages": {
            "python-teamcity-messages": {
                "downstream_package_name": "python-teamcity-messages",
                "paths": ["."],
                "specfile_path": "python-teamcity-messages.spec",
                "files_to_sync": ["python-teamcity-messages.spec", ".packit.yaml"],
                "upstream_package_name": "teamcity-messages",
                "upstream_tag_template": "v{version}"
            },
            "python-teamcity-messages-fake": {
                "downstream_package_name": "python-teamcity-messages-fake",
                "paths": ["."],
                "specfile_path": "python-teamcity-messages.spec",
                "files_to_sync": ["python-teamcity-messages.spec", ".packit.yaml"],
                "upstream_package_name": "teamcity-messages",
                "upstream_tag_template": "v{version}"
            }
        },
        "jobs": [
            {
                "job": "copr_build",
                "trigger": "commit",
                "targets": ["fedora-rawhide", "fedora-stable"],
                "packages": ["python-teamcity-messages-fake"]
            },
            {
                "job": "propose_downstream",
                "trigger": "release",
                "dist_git_branches": ["fedora-rawhide", "fedora-stable"],
                "packages": ["python-teamcity-messages-fake"]
            },
            {
                "job": "koji_build",
                "trigger": "commit",
                "allowed_pr_authors": ["packit"],
                "dist_git_branches": ["fedora-rawhide", "fedora-stable"],
                "packages": ["python-teamcity-messages-fake"]
            },
            {
                "job": "bodhi_update",
                "trigger": "commit",
                "dist_git_branches": ["fedora-rawhide", "fedora-stable"],
                "packages": ["python-teamcity-messages-fake"]
            }
        ]
    }
    """


@pytest.mark.parametrize(
    "package_config_yaml,how_many_builds",
    [
        pytest.param(DEFAULT_CONFIG_YAML, 1, id="default package config"),
        pytest.param(MONOREPO_CONFIG_YAML, 2, id="monorepo package config"),
    ],
)
def test_koji_build(package_config_yaml, how_many_builds):
    package_config_dict = json.loads(package_config_yaml)

    flexmock(package_config).should_receive("find_packit_yaml").and_return(
        flexmock(name=".packit.yaml", parent="/some/dir/teamcity-messages"),
    )
    flexmock(package_config).should_receive("load_packit_yaml").and_return(
        package_config_dict,
    )
    flexmock(LocalProject).should_receive("git_repo").and_return(
        flexmock(
            remotes=[],
            active_branch=flexmock(name="an active branch"),
            head=flexmock(is_detached=False),
        ),
    )
    # otherwise _dg and _local_project objects will be created
    # by debugger threads and you are not able to debug them
    flexmock(PackitAPI).should_receive("__repr__").and_return("")
    flexmock(DistGit).should_receive("__repr__").and_return("")
    flexmock(koji_build).should_receive("get_branches").and_return("rawhide")
    flexmock(PackitAPI).should_receive("init_kerberos_ticket").and_return()
    if how_many_builds == 1:
        flexmock(PackitAPI).should_receive("build").and_return().once()
    elif how_many_builds == 2:
        flexmock(PackitAPI).should_receive("build").and_return().twice()

    runner = CliRunner()
    runner.invoke(packit_base, ["build", "in-koji"])
