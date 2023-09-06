# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.utils.source_script import create_source_script


@pytest.mark.parametrize(
    "ref, pr_id, merge_pr, target_branch, job_config_index, url, command",
    [
        (
            None,
            None,
            True,
            None,
            None,
            "https://github.com/packit/ogr",
            'packit -d prepare-sources --result-dir "$resultdir" --no-create-symlinks '
            "https://github.com/packit/ogr",
        ),
        (
            "123",
            None,
            True,
            None,
            None,
            "https://github.com/packit/ogr",
            'packit -d prepare-sources --result-dir "$resultdir" --ref 123 --no-create-symlinks '
            "https://github.com/packit/ogr",
        ),
        (
            None,
            "1",
            False,
            None,
            None,
            "https://github.com/packit/ogr",
            'packit -d prepare-sources --result-dir "$resultdir" --pr-id 1 '
            "--no-merge-pr --no-create-symlinks https://github.com/packit/ogr",
        ),
        (
            None,
            "1",
            True,
            "main",
            None,
            "https://github.com/packit/ogr",
            'packit -d prepare-sources --result-dir "$resultdir" --pr-id 1 '
            "--merge-pr --target-branch main --no-create-symlinks https://github.com/packit/ogr",
        ),
        (
            None,
            "1",
            True,
            "main",
            0,
            "https://github.com/packit/ogr",
            'packit -d prepare-sources --result-dir "$resultdir" --pr-id 1 '
            "--merge-pr --target-branch main --job-config-index 0 "
            "--no-create-symlinks https://github.com/packit/ogr",
        ),
    ],
)
def test_create(ref, pr_id, merge_pr, target_branch, job_config_index, url, command):
    assert (
        create_source_script(
            ref=ref,
            pr_id=pr_id,
            merge_pr=merge_pr,
            target_branch=target_branch,
            job_config_index=job_config_index,
            url=url,
        )
        == f"""
#!/bin/sh

git config --global user.email "hello@packit.dev"
git config --global user.name "Packit"
resultdir=$PWD
{command}

"""
    )
