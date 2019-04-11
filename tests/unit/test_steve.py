"""
Let's test that Steve as awesome as we think he is.
"""
import pytest
from flexmock import flexmock
from github import Github
from ogr.services.github import GithubProject

from packit.api import PackitAPI
from packit.config import Config
from packit.jobs import SteveJobs
from packit.local_project import LocalProject


@pytest.mark.parametrize(
    "event",
    (
        (
            {
                "action": "published",
                "release": {"tag_name": "1.2.3"},
                "repository": {
                    "name": "bar",
                    "html_url": "https://github.com/foo/bar",
                    "owner": {"login": "foo"},
                },
            }
        ),
    ),
)
def test_process_message(event):
    packit_yaml = (
        "{'specfile_path': '', 'synced_files': []"
        ", jobs: [{trigger: release, job: propose_downstream}]}"
    )
    flexmock(Github, get_repo=lambda full_name_or_id: None)
    flexmock(
        GithubProject,
        get_file_content=lambda path, ref: packit_yaml,
        full_repo_name="foo/bar",
    )
    flexmock(LocalProject, refresh_the_arguments=lambda: None)
    flexmock(PackitAPI, sync_release=lambda dist_git_branch, version: None)
    c = Config()
    s = SteveJobs(c)
    s.process_message(event)
