# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import json
from pathlib import PosixPath

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


MONOREPO_COPR_PACKIT_YAML = """
    {
        "upstream_project_url": "https://github.com/fedora-copr/copr.git",
        "packages": {
            "python": {
                "downstream_package_name": "python-copr",
                "upstream_package_name": "copr",
                "paths": ["./python"],
                "specfile_path": "python-copr.spec",
                "files_to_sync": ["python-copr.spec"]
            },
            "cli": {
                "downstream_package_name": "copr-cli",
                "upstream_package_name": "copr-cli",
                "paths": ["./cli"],
                "specfile_path": "copr-cli.spec",
                "files_to_sync": ["copr-cli.spec"]
            },
            "frontend": {
                "downstream_package_name": "copr-frontend",
                "upstream_package_name": "copr-frontend",
                "paths": ["./frontend"],
                "specfile_path": "copr-frontend.spec",
                "files_to_sync": ["copr-frontend.spec"]
            }
        },
        "jobs": [
            {
                "job": "copr_build",
                "packages": ["cli", "python"],
                "trigger": "pull_request",
                "targets": "fedora-37",
                "owner": "mmassari",
                "project": "knx-stack"
            },
            {
                "job": "vm_image_build",
                "packages": ["cli", "python"],
                "trigger": "pull_request",
                "copr_chroot": "fedora-37-x86_64",
                "owner": "mmassari",
                "project": "knx-stack",
                "image_customizations": {
                    "packages": ["python-copr", "copr-cli"],
                    "image_distribution": "fedora-37",
                    "image_request": {
                        "architecture": "x86_64",
                        "image_type": "aws",
                        "upload_request": {
                            "type": "aws",
                            "options": {}
                        }
                    }
                }
            }
        ]
    }
    """


@pytest.mark.parametrize(
    "package_config_yaml,mock_api_calls,how_many_times,options",
    [
        pytest.param(
            DEFAULT_CONFIG_YAML,
            [("run_copr_build", ("build_id", "repo_url")), ("watch_copr_build", None)],
            1,
            ["build", "in-copr", "."],
            id="default package config copr build",
        ),
        pytest.param(
            MONOREPO_COPR_PACKIT_YAML,
            [("run_copr_build", ("build_id", "repo_url")), ("watch_copr_build", None)],
            2,
            ["build", "in-copr", "--package=python", "--package=cli"],
            id="monorepo build in copr for python and cli copr packages",
        ),
        pytest.param(
            MONOREPO_COPR_PACKIT_YAML,
            [("run_copr_build", ("build_id", "repo_url")), ("watch_copr_build", None)],
            0,
            ["build", "in-copr", "--package=python", "--package=unknown"],
            id=(
                "monorepo build in copr fails before any action is taken "
                "if a package does not exist"
            ),
        ),
        pytest.param(
            MONOREPO_COPR_PACKIT_YAML,
            [("run_copr_build", ("build_id", "repo_url")), ("watch_copr_build", None)],
            3,
            ["build", "in-copr", "."],
            id="monorepo copr build for all copr packages",
        ),
        pytest.param(
            DEFAULT_CONFIG_YAML,
            [("submit_vm_image_build", "build_id")],
            0,  # there is no image builder job definition
            ["build", "in-image-builder", "--no-wait", "."],
            id="default package config image build",
        ),
        pytest.param(
            MONOREPO_COPR_PACKIT_YAML,
            [("submit_vm_image_build", "build_id")],
            2,
            [
                "build",
                "in-image-builder",
                "--no-wait",
                "--package=python",
                "--package=cli",
                ".",
            ],
            id="monorepo build in image builder for python and cli copr packages",
        ),
        pytest.param(
            MONOREPO_COPR_PACKIT_YAML,
            [("submit_vm_image_build", "build_id")],
            2,  # there is no image builder job definition for frontend package (will fail)
            ["build", "in-image-builder", "--no-wait", "."],
            id="monorepo build in image builder for all copr packages",
        ),
        pytest.param(
            DEFAULT_CONFIG_YAML,
            [("create_srpm", "srpm_path")],
            1,
            ["srpm", "."],
            id="default package config srpm build",
        ),
        pytest.param(
            MONOREPO_COPR_PACKIT_YAML,
            [("create_srpm", "srpm_path")],
            2,
            ["srpm", "--package=cli", "--package=frontend"],
            id="monorepo srpm build for frontend and cli copr packages",
        ),
        pytest.param(
            MONOREPO_COPR_PACKIT_YAML,
            [("create_srpm", "srpm_path")],
            3,
            ["srpm", "."],
            id="monorepo srpm build for all copr packages",
        ),
    ],
)
def test_iterate_packages(package_config_yaml, mock_api_calls, how_many_times, options):
    package_config_dict = json.loads(package_config_yaml)

    flexmock(package_config).should_receive("find_packit_yaml").and_return(
        flexmock(name=".packit.yaml", parent="/some/dir/"),
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
    for call, result in mock_api_calls:
        flexmock(PackitAPI).should_receive(call).and_return(result).times(
            how_many_times,
        )

    runner = CliRunner()
    runner.invoke(packit_base, options)


@pytest.mark.parametrize(
    "package_config_yaml,mock_api_calls,how_many_times,options,dist_git,dist_git_is_git_repo",
    [
        pytest.param(
            DEFAULT_CONFIG_YAML,
            [("sync_status_string", None)],
            1,
            [
                "source-git",
                "status",
                ".",
                ".",
            ],  # fake dist-git dir for click safety checks
            "python-teamcity-messages",  # mocked dist-git value
            True,
            id="source git status for a default config",
        ),
        pytest.param(
            DEFAULT_CONFIG_YAML,
            [("sync_status_string", None)],
            1,
            [
                "source-git",
                "status",
                ".",
                ".",
            ],  # fake dist-git dir for click safety checks
            "teamcity-messages",  # mocked dist-git value
            True,
            id="source git status for a default config with no matching dist-git repo name",
        ),
        pytest.param(
            DEFAULT_CONFIG_YAML,
            [("sync_status_string", None)],
            0,
            [
                "source-git",
                "status",
                ".",
                ".",
            ],  # fake dist-git dir for click safety checks
            "teamcity-messages",  # mocked dist-git value
            False,
            id="source git status for a default config with no matching dist-git dir",
        ),
        pytest.param(
            MONOREPO_COPR_PACKIT_YAML,
            [("sync_status_string", None)],
            1,
            [
                "source-git",
                "status",
                ".",
                ".",
            ],  # fake dist-git dir for click safety checks
            "copr-cli",  # mocked dist-git value
            True,
            id="source git status for monorepo copr package copr-cli",
        ),
        pytest.param(
            MONOREPO_COPR_PACKIT_YAML,
            [("sync_status_string", None)],
            1,
            [
                "source-git",
                "status",
                ".",
                ".",
            ],  # fake dist-git dir for click safety checks
            "rpms",  # mocked dist-git value
            False,
            id="source git status for all the monorepo copr packages",
        ),
    ],
)
def test_iterate_packages_source_git(
    package_config_yaml,
    mock_api_calls,
    how_many_times,
    options,
    dist_git,
    dist_git_is_git_repo,
):
    package_config_dict = json.loads(package_config_yaml)
    flexmock(PosixPath).should_receive("name").and_return(dist_git)
    flexmock(PosixPath).should_call("joinpath").with_args(str)
    flexmock(PosixPath).should_receive("joinpath").with_args(".git").and_return(
        flexmock().should_receive("exists").and_return(dist_git_is_git_repo).mock(),
    )
    flexmock(PosixPath).should_receive("glob").and_return(
        [
            flexmock(is_dir=lambda: True, name="copr-cli")
            .should_receive("joinpath")
            .and_return(flexmock().should_receive("exists").and_return(True).mock())
            .mock(),
        ],
    )

    flexmock(package_config).should_receive("load_packit_yaml").and_return(
        package_config_dict,
    )
    # otherwise _dg and _local_project objects will be created
    # by debugger threads and you are not able to debug them
    flexmock(PackitAPI).should_receive("__repr__").and_return("")
    for call, result in mock_api_calls:
        flexmock(PackitAPI).should_receive(call).and_return(result).times(
            how_many_times,
        )

    runner = CliRunner()
    runner.invoke(packit_base, options)
