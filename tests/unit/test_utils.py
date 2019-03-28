import pytest
from packit.exceptions import PackitException

from packit.utils import get_namespace_and_repo_name


@pytest.mark.parametrize(
    "url,namespace,repo_name",
    [
        ("https://github.com/org/name", "org", "name"),
        ("https://github.com/org/name.git", "org", "name"),
        ("git@github.com:org/name", "org", "name"),
        ("git@github.com:org/name.git", "org", "name"),
    ],
)
def test_get_ns_repo(url, namespace, repo_name):
    assert get_namespace_and_repo_name(url) == (namespace, repo_name)


def test_get_ns_repo_exc():
    url = "git@github.com"
    with pytest.raises(PackitException) as ex:
        get_namespace_and_repo_name(url)
    msg = f"Invalid URL format, can't obtain namespace and repository name: {url}"
    assert msg in str(ex.value)
