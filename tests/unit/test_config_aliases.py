import pytest

from packit.config.aliases import (
    get_versions,
    get_build_targets,
    get_branches,
    ALIASES,
    get_koji_targets,
    get_all_koji_targets,
)
from packit.exceptions import PackitException
from tests.spellbook import ALL_KOJI_TARGETS_SNAPSHOT


@pytest.mark.parametrize(
    "name,versions",
    [
        ("fedora-29", {"fedora-29"}),
        ("epel-8", {"epel-8"}),
        ("fedora-rawhide", {"fedora-rawhide"}),
        ("openmandriva-rolling", {"openmandriva-rolling"}),
        ("opensuse-leap-15.0", {"opensuse-leap-15.0"}),
        ("fedora-stable", {"fedora-31", "fedora-32"}),
        ("fedora-development", {"fedora-rawhide"}),
        ("fedora-all", {"fedora-rawhide", "fedora-31", "fedora-32"}),
        ("centos-stream", {"centos-stream"}),
    ],
)
def test_get_versions(name, versions):
    assert get_versions(name) == versions


@pytest.mark.parametrize(
    "names,versions",
    [
        (["fedora-30", "fedora-stable"], {"fedora-30", "fedora-31", "fedora-32"},),
        (["fedora-31", "fedora-stable"], {"fedora-31", "fedora-32"}),
        ([], {"fedora-31", "fedora-32"}),
    ],
)
def test_get_versions_from_multiple_values(names, versions):
    assert get_versions(*names) == versions


def test_get_versions_empty_without_default():
    assert get_versions(default=None) == set()


@pytest.mark.parametrize(
    "name,targets",
    [
        ("rawhide", {"fedora-rawhide-x86_64"}),
        ("fedora-29", {"fedora-29-x86_64"}),
        ("epel-8", {"epel-8-x86_64"}),
        ("fedora-rawhide", {"fedora-rawhide-x86_64"}),
        ("openmandriva-rolling", {"openmandriva-rolling-x86_64"}),
        ("opensuse-leap-15.0", {"opensuse-leap-15.0-x86_64"}),
        ("centos-stream", {"centos-stream-x86_64"}),
        ("centos-stream-x86_64", {"centos-stream-x86_64"}),
        ("fedora-stable", {"fedora-31-x86_64", "fedora-32-x86_64"}),
        ("fedora-development", {"fedora-rawhide-x86_64"}),
        ("fedora-29-x86_64", {"fedora-29-x86_64"}),
        ("fedora-29-aarch64", {"fedora-29-aarch64"}),
        ("fedora-29-i386", {"fedora-29-i386"}),
        ("fedora-stable-aarch64", {"fedora-31-aarch64", "fedora-32-aarch64"},),
        ("fedora-development-aarch64", {"fedora-rawhide-aarch64"}),
        (
            "fedora-all",
            {"fedora-rawhide-x86_64", "fedora-31-x86_64", "fedora-32-x86_64"},
        ),
    ],
)
def test_get_build_targets(name, targets):
    assert get_build_targets(name) == targets


def test_get_build_targets_invalid_input():
    name = "rafhajd"
    with pytest.raises(PackitException) as ex:
        get_build_targets(name)
    err_msg = (
        f"Cannot get build target from '{name}'"
        f", packit understands values like these: '{list(ALIASES.keys())}'."
    )
    assert str(ex.value) == err_msg


def test_get_build_targets_without_default():
    assert get_build_targets(default=None) == set()


@pytest.mark.parametrize(
    "names,versions",
    [
        (
            ["fedora-30", "fedora-stable"],
            {"fedora-30-x86_64", "fedora-31-x86_64", "fedora-32-x86_64"},
        ),
        (["fedora-31", "fedora-stable"], {"fedora-31-x86_64", "fedora-32-x86_64"},),
    ],
)
def test_get_build_targets_from_multiple_values(names, versions):
    assert get_build_targets(*names) == versions


@pytest.mark.parametrize(
    "name,branches",
    [
        ("fedora-29", {"f29"}),
        ("fedora-rawhide", {"master"}),
        ("rawhide", {"master"}),
        ("master", {"master"}),
        ("f30", {"f30"}),
        ("fedora-development", {"master"}),
        ("fedora-stable", {"f31", "f32"}),
        ("epel-7", {"epel7"}),
        ("epel7", {"epel7"}),
        ("el6", {"el6"}),
        ("epel-6", {"el6"}),
        ("fedora-all", {"master", "f31", "f32"}),
    ],
)
def test_get_branches(name, branches):
    assert get_branches(name) == branches


@pytest.mark.parametrize(
    "names,versions",
    [
        (["fedora-30", "fedora-stable"], {"f30", "f31", "f32"}),
        (["fedora-31", "fedora-stable"], {"f31", "f32"}),
    ],
)
def test_get_branches_from_multiple_values(names, versions):
    assert get_branches(*names) == versions


def test_get_branches_without_default():
    assert get_branches(default=None) == set()


@pytest.mark.parametrize("target", ALL_KOJI_TARGETS_SNAPSHOT)
def test_preserve_koji_targets_single(target):
    assert {target} == get_koji_targets(target)


def test_preserve_all_koji_targets_together():
    assert set(ALL_KOJI_TARGETS_SNAPSHOT) == get_koji_targets(
        *ALL_KOJI_TARGETS_SNAPSHOT
    )


@pytest.mark.parametrize(
    "name,targets",
    [
        ("fedora-29", {"f29"}),
        ("fedora-rawhide", {"rawhide"}),
        ("rawhide", {"rawhide"}),
        ("master", {"master"}),
        ("f30", {"f30"}),
        ("fedora-development", {"rawhide"}),
        ("fedora-stable", {"f31", "f32"}),
        ("epel-7", {"epel7"}),
        ("epel7", {"epel7"}),
        ("el6", {"epel6"}),
        ("epel-6", {"epel6"}),
        ("fedora-all", {"rawhide", "f31", "f32"}),
        ("epel-all", {"epel6", "epel7", "epel8"}),
    ],
)
def test_get_koji_targets(name, targets):
    assert get_koji_targets(name) == targets


def test_get_koji_targets_without_default():
    assert get_koji_targets(default=None) == set()


def test_get_all_koji_targets():
    targets = get_all_koji_targets()
    assert targets
    assert "Name" not in targets
    assert "rawhide" in targets
    assert "epel8" in targets
    assert all(isinstance(target, str) for target in targets)
