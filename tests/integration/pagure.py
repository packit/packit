import os

import pytest
from libpagure import APIError

from onegittorulethemall.services.pagure import PagureService


@pytest.fixture()
def pagure_token():
    return os.environ["PAGURE_API_TOKEN"]


@pytest.fixture()
def pagure_service(pagure_token):
    return PagureService(token=pagure_token)


@pytest.fixture()
def docker_py_project(pagure_service):
    docker_py = pagure_service.get_project(namespace="rpms", repo="python-docker-py",
                                           username="lachmanfrantisek")
    return docker_py


@pytest.fixture()
def abiword_project(pagure_service):
    abiword = pagure_service.get_project(
        namespace="rpms", repo="abiword", username="churchyard"
    )
    return abiword


@pytest.fixture()
def abiword_project_fork(pagure_service):
    abiword = pagure_service.get_project(
        namespace="rpms", repo="abiword", username="churchyard", is_fork=True
    )
    return abiword


@pytest.fixture()
def abiword_project_non_existing_fork(pagure_service):
    abiword = pagure_service.get_project(
        namespace="rpms", repo="abiword", username="qwertzuiopasdfghjkl", is_fork=True
    )
    return abiword


def test_decsription(docker_py_project):
    description = docker_py_project.description
    assert description == "The python-docker-py rpms"


def test_branches(docker_py_project):
    branches = docker_py_project.branches
    assert branches
    assert branches == [
        "el6",
        "epel7",
        "f19",
        "f20",
        "f21",
        "f22",
        "f23",
        "f24",
        "f25",
        "f26",
        "f27",
        "f28",
        "master",
        "private-ttomecek-push-to-tls-registries-without-auth",
    ]


def test_git_urls(docker_py_project):
    urls = docker_py_project.git_urls
    assert urls
    assert len(urls) == 2
    assert "git" in urls
    assert "ssh" in urls
    assert urls["git"] == "https://src.fedoraproject.org/rpms/python-docker-py.git"
    assert urls["ssh"].endswith("@pkgs.fedoraproject.org/rpms/python-docker-py.git")


def test_pr_list(abiword_project):
    pr_list = abiword_project.pr_list()
    assert isinstance(pr_list, list)
    assert not pr_list

    pr_list = abiword_project.pr_list(status="All")
    assert pr_list
    assert len(pr_list) == 2


def test_pr_info(abiword_project):
    pr_info = abiword_project.pr_info(pr_id=1)
    assert pr_info
    assert pr_info["title"].startswith("Update Python 2 dependency")
    assert pr_info["status"] == "Merged"


def test_commit_flags(abiword_project):
    flags = abiword_project.get_commit_flags(
        commit="d87466de81c72231906a6597758f37f28830bb71"
    )
    assert isinstance(flags, list)
    assert len(flags) == 0


def test_fork(abiword_project_fork):
    assert abiword_project_fork.exists
    fork_description = abiword_project_fork.description
    assert fork_description


def test_nonexisting_fork(abiword_project_non_existing_fork):
    assert not abiword_project_non_existing_fork.exists
    with pytest.raises(APIError) as ex:
        _ = abiword_project_non_existing_fork.description
    assert "Project not found" in ex.value.args


def test_fork_property(abiword_project):
    fork = abiword_project.fork
    assert fork
    assert fork.description


def test_create_fork(docker_py_project):
    assert not docker_py_project.fork
    docker_py_project.fork_create()
    assert docker_py_project.fork.exists
