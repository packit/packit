# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.cli.prepare_sources import load_job_config
from packit.config import CommonPackageConfig, JobConfig, JobConfigTriggerType, JobType


@pytest.mark.parametrize(
    "raw_job_config,expected",
    [
        pytest.param(
            """\
            {
                "job": "copr_build",
                "trigger": "release",
                "skip_build": false,
                "manual_trigger": false,
                "packages": {
                    "package": {
                        "upstream_package_name": null,
                        "downstream_package_name": "package",
                        "archive_root_dir_template": "{upstream_pkg_name}-{version}",
                        "patch_generation_ignore_paths": [],
                        "dist_git_namespace": "rpms",
                        "actions": {},
                        "upstream_project_url": null,
                        "sources": [],
                        "create_pr": true,
                        "merge_pr_in_ci": true,
                        "upstream_ref": null,
                        "upstream_tag_template": "{version}",
                        "config_file_path": null,
                        "files_to_sync": [],
                        "sync_changelog": false,
                        "patch_generation_patch_id_digits": 4,
                        "preserve_project": false,
                        "branch": null,
                        "additional_repos": [],
                        "env": {},
                        "additional_packages": [],
                        "scratch": false,
                        "targets": {},
                        "fmf_url": null,
                        "fmf_ref": null,
                        "fmf_path": null,
                        "owner": null,
                        "use_internal_tf": false,
                        "list_on_homepage": false,
                        "project": "example1",
                        "dist_git_branches": [],
                        "timeout": 7200,
                        "notifications": {
                            "pull_request": {
                                "successful_build": false
                            }
                        },
                        "copy_upstream_release_description": false,
                        "specfile_path": "package.spec",
                        "dist_git_base_url": "https://src.fedoraproject.org/",
                        "spec_source_id": "Source0",
                        "allowed_gpg_keys": null,
                        "tmt_plan": null,
                        "tf_post_install_script": null
                    }
                }
            }
            """,
            JobConfig(
                type=JobType.copr_build,
                trigger=JobConfigTriggerType.release,
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="package",
                        specfile_path="package.spec",
                        project="example1",
                    ),
                },
            ),
            id="valid",
        ),
        pytest.param('{"config_file_path": null}', None, id="invalid"),
    ],
)
def test_load_job_config(raw_job_config, expected):
    assert load_job_config(raw_job_config) == expected
