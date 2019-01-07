import pytest

from onegittorulethemall.services.pagure import (
    PagureService,
    sanitize_fork_username,
)


@pytest.fixture()
def pagure_service():
    return PagureService(token="12345", instance_url="https://pagure.pagure")


@pytest.fixture()
def pagure_service_username():
    return PagureService(
        token="12345", instance_url="https://pagure.pagure", username="nobody"
    )


@pytest.fixture()
def test_project(pagure_service):
    test_project = pagure_service.get_project(repo="my-test-project", namespace="rpms")
    return test_project


def test_repo(test_project):
    assert test_project.repo == "my-test-project"
    assert test_project.pagure.repo_name == "my-test-project"
    assert test_project.pagure.repo == "rpms/my-test-project"


def test_namespace(test_project):
    assert test_project.namespace == "rpms"
    assert test_project.pagure.namespace == "rpms"


def test_api_url(pagure_service):
    assert pagure_service.pagure.api_url == "https://pagure.pagure/api/0/"


@pytest.mark.parametrize(
    "args_list,result",
    [
        ([], "https://pagure.pagure/api/0/"),
        (["something"], "https://pagure.pagure/api/0/something"),
        (["a", "b", "c", "d"], "https://pagure.pagure/api/0/a/b/c/d"),
    ],
)
def test_get_api_url(pagure_service, args_list, result):
    assert pagure_service.pagure.get_api_url(*args_list) == result


@pytest.mark.parametrize(
    "args_list,result",
    [
        ([], "https://pagure.pagure/api/0/fork/nobody"),
        (["something"], "https://pagure.pagure/api/0/fork/nobody/something"),
        (["a", "b", "c", "d"], "https://pagure.pagure/api/0/fork/nobody/a/b/c/d"),
    ],
)
def test_get_api_url_username(pagure_service_username, args_list, result):
    assert pagure_service_username.pagure.get_api_url(*args_list) == result


@pytest.mark.parametrize(
    "dictionary,result",
    [
        ({}, {}),
        ({"a": "b"}, {"a": "b"}),
        ({"username": "nobody"}, {"fork_username": "nobody"}),
        (
                {"username": "nobody", "fork_username": "somebody"},
                {"username": "nobody", "fork_username": "somebody"},
        ),
    ],
)
def test_replace_username_with_username(dictionary, result):
    assert sanitize_fork_username(dictionary) == result


def test_non_fork(pagure_service_username):
    test_project = pagure_service_username.get_project(repo="my-test-project", namespace="rpms")
    assert not test_project.is_fork
    assert not test_project.pagure.username


def test_fork(pagure_service_username):
    test_project = pagure_service_username.get_project(
        repo="my-test-project", namespace="rpms", is_fork=True
    )
    assert test_project.is_fork
    assert test_project.pagure.username == "nobody"
