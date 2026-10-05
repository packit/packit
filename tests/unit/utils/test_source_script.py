# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import textwrap

import pytest

from packit.utils.source_script import (
    create_distgit_source_script,
    create_source_script,
)


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


@pytest.mark.parametrize(
    "ref, pr_id, merge_pr, target_branch, package, dist_git, custom_steps, url",
    [
        (
            "feature-branch",
            "12345",
            True,
            "main",
            "ogr",
            "rhel",
            textwrap.dedent(
                """
                git remote add source https://gitlab.com/packit/ogr

                git fetch source refs/merge-requests/12345/head:refs/packit/pr-head
                git fetch origin main:refs/packit/target

                git checkout --detach refs/packit/target
                git merge --no-ff --no-edit refs/packit/pr-head
                """,
            ).strip(),
            "https://gitlab.com/packit/ogr",
        ),
        (
            "feature-branch",
            "12345",
            False,
            "main",
            "ogr",
            "rhel",
            textwrap.dedent(
                """\
                git remote add source https://gitlab.com/packit/ogr

                git fetch source refs/merge-requests/12345/head
                git checkout --detach FETCH_HEAD
                """,
            ).strip(),
            "https://gitlab.com/packit/ogr",
        ),
        (
            "abcdefghij12345",
            None,
            False,
            None,
            "ogr",
            "rhel",
            textwrap.dedent(
                """
                git fetch origin abcdefghij12345
                git checkout --detach FETCH_HEAD
                """,
            ).strip(),
            "https://gitlab.com/packit/ogr",
        ),
        (
            "v1.2.0",
            None,
            False,
            None,
            "ogr",
            "rhel",
            textwrap.dedent(
                """
                git fetch origin v1.2.0
                git checkout --detach FETCH_HEAD
                """,
            ).strip(),
            "https://gitlab.com/packit/ogr",
        ),
    ],
)
def test_create_from_dist_git(
    ref,
    pr_id,
    merge_pr,
    target_branch,
    package,
    dist_git,
    custom_steps,
    url,
):

    expected = textwrap.dedent(
        """
        #!/bin/sh

        # exit on error
        set -e

        git config --global user.email "hello@packit.dev"
        git config --global user.name "Packit"

        dist-git-client clone ogr --dist-git rhel
        cd ogr

        # custom steps
        # depend on whether this Copr build is submitted
        # as a result of a commit, pull-request or release trigger
        __CUSTOM_STEPS__

        dist-git-client sources
        dist-git-client srpm --outputdir .
        bsdtar xf *.src.rpm -C "$COPR_RESULTDIR"

        """,
    ).replace("__CUSTOM_STEPS__", custom_steps)

    result = create_distgit_source_script(
        ref=ref,
        pr_id=pr_id,
        url=url,
        merge_pr=merge_pr,
        target_branch=target_branch,
        package=package,
        dist_git=dist_git,
    )

    assert expected == result
