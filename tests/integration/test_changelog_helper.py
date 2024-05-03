# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import subprocess
from logging import getLogger

import pytest
import rpm
from flexmock import flexmock

from packit.actions import ActionName
from packit.config.package_config import PackageConfig
from packit.distgit import DistGit
from packit.utils.changelog_helper import ChangelogHelper

logger = getLogger(__name__)


@pytest.fixture
def package_config():
    yield PackageConfig()


@pytest.fixture
def upstream(upstream_instance):
    _, ups = upstream_instance
    yield ups


@pytest.fixture
def downstream():
    yield flexmock(DistGit)


def test_srpm_action(upstream, downstream):
    package_config = upstream.package_config
    package_config.actions = {
        ActionName.changelog_entry: [
            "echo - hello from test_srpm_action   ",
        ],
    }

    ChangelogHelper(upstream, downstream, package_config).prepare_upstream_locally(
        "0.1.0",
        "abc123a",
        True,
        None,
    )
    with upstream.specfile.sections() as sections:
        assert "- hello from test_srpm_action" in sections.changelog


def test_srpm_commits(upstream, downstream):
    package_config = upstream.package_config
    ChangelogHelper(upstream, downstream, package_config).prepare_upstream_locally(
        "0.1.0",
        "abc123a",
        True,
        None,
    )
    with upstream.specfile.sections() as sections:
        assert "- Development snapshot (abc123a)" in sections.changelog


def test_srpm_no_tags(upstream, downstream):
    package_config = upstream.package_config
    flexmock(upstream).should_receive("get_last_tag").and_return(None).once()

    ChangelogHelper(upstream, downstream, package_config).prepare_upstream_locally(
        "0.1.0",
        "abc123a",
        True,
        None,
    )
    with upstream.specfile.sections() as sections:
        assert "- Development snapshot (abc123a)" in sections.changelog


def test_srpm_no_bump(upstream, downstream):
    package_config = upstream.package_config
    flexmock(upstream).should_receive("get_last_tag").and_return(None).once()

    ChangelogHelper(upstream, downstream, package_config).prepare_upstream_locally(
        "0.1.0",
        "abc123a",
        False,
        None,
    )
    with upstream.specfile.sections() as sections:
        assert "- Development snapshot (abc123a)" not in sections.changelog


def test_update_distgit_when_copy_upstream_release_description(
    upstream,
    distgit_instance,
):
    _, downstream = distgit_instance
    package_config = upstream.package_config
    package_config.copy_upstream_release_description = True
    upstream.local_project.git_project = (
        flexmock()
        .should_receive("get_release")
        .with_args(tag_name="0.1.0", name="0.1.0")
        .and_return(flexmock(body="Some release 0.1.0"))
        .mock()
    )

    ChangelogHelper(upstream, downstream, package_config).update_dist_git(
        upstream_tag="0.1.0",
        full_version="0.1.0",
        resolved_bugs=["rhbz#123"],
    )

    with downstream._specfile.sections() as sections:
        assert "Some release 0.1.0" in sections.changelog
        assert "- Resolves: rhbz#123" in sections.changelog


@pytest.mark.skipif(
    rpm.__version__ < "4.16",
    reason="%autochangelog requires rpm 4.16 or higher",
)
def test_do_not_update_distgit_with_autochangelog(
    upstream,
    distgit_instance_with_autochangelog,
):
    _, downstream = distgit_instance_with_autochangelog
    package_config = upstream.package_config

    ChangelogHelper(upstream, downstream, package_config).update_dist_git(
        upstream_tag="0.1.0",
        full_version="0.1.0",
    )

    with downstream._specfile.sections() as sections:
        assert "%autochangelog" in sections.changelog


def test_update_distgit_unsafe_commit_messages(upstream, distgit_instance):
    _, downstream = distgit_instance
    package_config = upstream.package_config
    flexmock(upstream).should_receive("get_commit_messages").and_return(
        "* 100% of tests now pass\n"
        "* got rid of all shell (%(...)) and expression (%[...]) expansions\n"
        "* removed all %global macros\n"
        "* cleaned up %install section\n",
    )

    ChangelogHelper(upstream, downstream, package_config).update_dist_git(
        upstream_tag="0.1.0",
        full_version="0.1.0",
    )

    # make sure only one changelog entry (as seen by RPM) has been added
    downstream.specfile.macros.append(("_changelog_trimage", "0"))
    downstream.specfile.macros.append(("_changelog_trimtime", "0"))
    assert len(downstream.specfile.rpm_spec.sourceHeader[rpm.RPMTAG_CHANGELOGTEXT]) == 2


def test_update_distgit_when_copy_upstream_release_description_none(
    upstream,
    distgit_instance,
):
    _, downstream = distgit_instance
    package_config = upstream.package_config
    package_config.copy_upstream_release_description = True
    upstream.local_project.git_project = (
        flexmock()
        .should_receive("get_release")
        .with_args(tag_name="0.1.0", name="0.1.0")
        .and_return(flexmock(body=None))
        .mock()
    )

    ChangelogHelper(upstream, downstream, package_config).update_dist_git(
        upstream_tag="0.1.0",
        full_version="0.1.0",
    )

    with downstream._specfile.sections() as sections:
        assert "- Update to version 0.1.0" in sections.changelog


def test_update_distgit_changelog_entry_action_pass_env_vars(
    upstream,
    distgit_instance,
):
    _, downstream = distgit_instance
    package_config = upstream.package_config
    package_config.actions = {ActionName.changelog_entry: "command"}
    upstream.local_project.git_project = (
        flexmock()
        .should_receive("get_release")
        .with_args(tag_name="0.1.0", name="0.1.0")
        .and_return(flexmock(body="Some release 0.1.0"))
        .mock()
    )
    expected_env = {
        "PACKIT_CONFIG_PACKAGE_NAME": "beer",
        "PACKIT_UPSTREAM_PACKAGE_NAME": "beerware",
        "PACKIT_DOWNSTREAM_PACKAGE_NAME": "beer",
        "PACKIT_PROJECT_VERSION": "0.1.0",
        "PACKIT_RESOLVED_BUGS": "rhbz#123 rhbz#124",
        "PACKIT_PROJECT_UPSTREAM_TAG": "0.1.0",
        "PACKIT_PROJECT_PREVIOUS_VERSION": "0.0.0",
    }
    flexmock(upstream.actions_handler).should_receive(
        "get_output_from_action",
    ).with_args(
        ActionName.changelog_entry,
        env=expected_env,
    ).and_return(
        "- entry",
    ).once()

    ChangelogHelper(upstream, downstream, package_config).update_dist_git(
        upstream_tag="0.1.0",
        full_version="0.1.0",
        resolved_bugs=["rhbz#123", "rhbz#124"],
    )


def test_update_distgit_no_distgit_specfile(
    upstream,
    distgit_instance,
):
    d, downstream = distgit_instance
    # remove the downstream specfile
    d.joinpath("beer.spec").unlink()
    subprocess.check_call(
        ["git", "commit", "-m", "remove spec", "-a"],
        cwd=str(d),
    )
    package_config = upstream.package_config
    package_config.copy_upstream_release_description = True
    upstream.local_project.git_project = (
        flexmock()
        .should_receive("get_release")
        .with_args(tag_name="0.1.0", name="0.1.0")
        .and_return(flexmock(body="Some release 0.1.0"))
        .mock()
    )

    ChangelogHelper(upstream, downstream, package_config).update_dist_git(
        upstream_tag="0.1.0",
        full_version="0.1.0",
    )

    with downstream._specfile.sections() as sections:
        assert "Some release 0.1.0" in sections.changelog
