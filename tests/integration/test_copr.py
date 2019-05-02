import json

import copr.v3.proxies as proxies
import pytest
from copr.v3 import Client
from flexmock import flexmock
from github import Github
from munch import Munch
from ogr.services.github import GithubProject

from packit.api import PackitAPI
from packit.config import get_local_package_config, Config
from packit.exceptions import PackitInvalidConfigException
from packit.jobs import SteveJobs
from packit.local_project import LocalProject
from packit.utils import cwd
from tests.spellbook import get_test_config, DATA_DIR


@pytest.fixture()
def copr_project():
    return Munch(
        {
            "additional_repos": [],
            "auto_prune": True,
            "chroot_repos": {
                "fedora-rawhide-x86_64": "https://copr-be.cloud.fedoraproject.org/"
                "results/packit/dummy/fedora-rawhide-x86_64/"
            },
            "contact": "",
            "description": "",
            "devel_mode": False,
            "enable_net": True,
            "full_name": "packit/dummy",
            "homepage": "",
            "id": 24041,
            "instructions": "",
            "name": "dummy",
            "ownername": "packit",
            "persistent": False,
            "unlisted_on_hp": False,
            "use_bootstrap_container": False,
            "__response__": "",
            "__proxy__": "",
        }
    )


@pytest.fixture()
def copr_build():
    return Munch(
        {
            "chroots": [],
            "ended_on": None,
            "id": 12345,
            "ownername": "packit",
            "project_dirname": "dummy",
            "projectname": "dummy",
            "repo_url": "https://copr-be.cloud.fedoraproject.org/results/packit/dummy",
            "source_package": {"name": None, "url": None, "version": None},
            "started_on": None,
            "state": "pending",
            "submitted_on": 1556189372,
            "submitter": "packit",
            "__response__": "",
            "__proxy__": "",
        }
    )


@pytest.fixture()
def pr_event():
    with open(DATA_DIR / "webhooks" / "github_pr_event.json", "r") as outfile:
        return json.load(outfile)


@pytest.fixture()
def release_event():
    with open(DATA_DIR / "webhooks" / "release_event.json", "r") as outfile:
        return json.load(outfile)


@pytest.fixture()
def test_copr_client():
    return Client.create_from_config_file(DATA_DIR / "copr_config")


def test_run_copr_build(upstream_n_distgit, copr_project, copr_build, test_copr_client):
    u, d = upstream_n_distgit

    with cwd(u):
        c = get_test_config()

        pc = get_local_package_config(str(u))
        pc.upstream_project_url = str(u)
        pc.downstream_project_url = str(d)
        up_lp = LocalProject(path_or_url=str(u))
        api = PackitAPI(c, pc, up_lp)

        flexmock(Client).should_receive("create_from_config_file").and_return(
            test_copr_client
        )

        # invalid owner + project
        with pytest.raises(PackitInvalidConfigException):
            api.run_copr_build("not-packit", "dummy", [])

        # with project chroots update
        flexmock(proxies.project.ProjectProxy).should_receive("get").and_return(
            copr_project
        ).once()
        flexmock(proxies.project.ProjectProxy).should_receive("edit").once()

        flexmock(proxies.build.BuildProxy).should_receive(
            "create_from_file"
        ).and_return(copr_build).once()
        id, url = api.run_copr_build("not-packit", "dummy", [""])
        assert id == 12345
        assert url == "https://copr-be.cloud.fedoraproject.org/results/packit/dummy"


@pytest.mark.skip
def test_copr_pr_handle(pr_event):
    packit_yaml = (
        "{'specfile_path': '', 'synced_files': []"
        ", jobs: [{trigger: pull_request, job: copr_build, "
        "metadata: {targets:['beer-again'], 'owner': 'Bilbo', 'project':'keg'}}]}"
    )
    flexmock(Github, get_repo=lambda full_name_or_id: None)
    flexmock(
        GithubProject,
        get_file_content=lambda path, ref: packit_yaml,
        full_repo_name="foo/bar",
    )
    flexmock(LocalProject, refresh_the_arguments=lambda: None)
    flexmock(PackitAPI, sync_release=lambda dist_git_branch, version: None)

    flexmock(PackitAPI).should_receive("run_copr_build").with_args(
        owner="Bilbo",
        project="keg",
        committish="34c5c7793cb3b279e22454cb6750c80560547b3a",
        clone_url="https://github.com/Codertocat/Hello-World.git",
        chroots=["beer-again"],
    ).and_return(1, "http://shire").once()
    flexmock(GithubProject).should_receive("pr_comment").with_args(
        pr_event["number"], "Triggered copr build (ID:1).\nMore info: http://shire"
    ).and_return().once()
    c = Config()
    s = SteveJobs(c)
    s.process_message(pr_event)


@pytest.mark.skip
def test_copr_release_handle(release_event):
    packit_yaml = (
        "{'specfile_path': '', 'synced_files': []"
        ", jobs: [{trigger: release, job: copr_build, metadata: {targets:[]}}]}"
    )
    flexmock(Github, get_repo=lambda full_name_or_id: None)
    flexmock(
        GithubProject,
        get_file_content=lambda path, ref: packit_yaml,
        full_repo_name="foo/bar",
    )
    flexmock(LocalProject, refresh_the_arguments=lambda: None)
    flexmock(PackitAPI, sync_release=lambda dist_git_branch, version: None)

    flexmock(PackitAPI).should_receive("run_copr_build").with_args(
        owner="packit",
        project="Codertocat-Hello-World",
        committish="0.0.1",
        clone_url="https://github.com/Codertocat/Hello-World.git",
        chroots=[],
    ).and_return(1, "http://shire").once()
    flexmock(GithubProject).should_receive("commit_comment").with_args(
        pr_event["number"], "Triggered copr build (ID:1).\nMore info: http://shire"
    ).and_return().once()

    c = Config()
    s = SteveJobs(c)
    s.process_message(release_event)


@pytest.mark.skip
def test_watch_build(upstream_n_distgit):
    u, d = upstream_n_distgit

    with cwd(u):
        c = get_test_config()

        pc = get_local_package_config(str(u))
        pc.upstream_project_url = str(u)
        pc.downstream_project_url = str(d)
        up_lp = LocalProject(path_or_url=str(u))
        api = PackitAPI(c, pc, up_lp)

        flexmock(proxies.build.BuildProxy).should_receive("get").and_return(
            Munch({"state": "pending"})
        )
        assert api.watch_copr_build(1, timeout=0) == "watch timeout"
