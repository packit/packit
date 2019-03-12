import pytest

from packit.utils import get_namespace


@pytest.mark.parametrize(
    "url,namespace",
    [
        ("https://github.com/org/name", "org"),
        ("git@github.com:org/name", "org"),
        ("https://git/foo/bar/2", "foo"),
        ("git@github.com:nothing/else/matters", "nothing"),
        ("http://git/org/name", "org"),
        ("https://some/org", "org"),
        ("https://some", None),
        ("git@github.com", None),
        ("git@github.com/foo/bar", None),
        ("git@github.com:foo", "foo"),
    ],
)
def test_job_config_validate(url, namespace):
    assert get_namespace(url) == namespace
