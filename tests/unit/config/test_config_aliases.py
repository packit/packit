# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
from collections import Counter

import pytest
from copr.v3 import Client
from flexmock import flexmock

import packit
from packit.config import CommonPackageConfig, aliases
from packit.config.aliases import (
    expand_aliases,
    get_aliases,
    get_all_koji_targets,
    get_branches,
    get_build_targets,
    get_fast_forward_merge_branches_for,
    get_koji_targets,
    opensuse_distro_aliases,
)
from packit.copr_helper import CoprHelper
from tests.spellbook import ALL_KOJI_TARGETS_SNAPSHOT


@pytest.mark.usefixtures("mock_get_aliases")
class TestExpandAliases:
    @pytest.mark.parametrize(
        "name,versions",
        [
            ("fedora-29", {"fedora-29"}),
            ("epel-8", {"epel-8"}),
            ("fedora-rawhide", {"fedora-rawhide"}),
            ("openmandriva-rolling", {"openmandriva-rolling"}),
            ("opensuse-leap-15.0", {"opensuse-leap-15.0"}),
            ("fedora-stable", {"fedora-31", "fedora-32"}),
            ("fedora-development", {"fedora-33", "fedora-rawhide"}),
            (
                "fedora-all",
                {
                    "fedora-29",
                    "fedora-30",
                    "fedora-31",
                    "fedora-32",
                    "fedora-33",
                    "fedora-rawhide",
                },
            ),
            ("centos-stream-8", {"centos-stream-8"}),
        ],
    )
    def test_expand_aliases(self, name, versions, mock_get_aliases):
        assert {
            v.namever if hasattr(v, "namever") else v for v in expand_aliases(name)
        } == versions

    @pytest.mark.parametrize(
        "names,versions",
        [
            (
                ["fedora-30", "fedora-stable"],
                {"fedora-30", "fedora-31", "fedora-32"},
            ),
            (["fedora-31", "fedora-stable"], {"fedora-31", "fedora-32"}),
            ([], {"fedora-31", "fedora-32"}),
        ],
    )
    def test_expand_aliases_from_multiple_values(self, names, versions):
        assert {
            v.namever if hasattr(v, "namever") else v for v in expand_aliases(*names)
        } == versions

    def test_expand_aliases_empty_without_default(self):
        assert expand_aliases(default=None) == set()


@pytest.mark.usefixtures("mock_get_aliases")
class TestGetBuildTargets:
    @pytest.mark.parametrize(
        "name,targets",
        [
            ("rawhide", {"fedora-rawhide-x86_64"}),
            ("fedora-29", {"fedora-29-x86_64"}),
            ("epel-8", {"epel-8-x86_64"}),
            ("fedora-rawhide", {"fedora-rawhide-x86_64"}),
            ("openmandriva-rolling", {"openmandriva-rolling-x86_64"}),
            ("opensuse-leap-15.0", {"opensuse-leap-15.0-x86_64"}),
            ("centos-stream", {"centos-stream-8-x86_64"}),
            ("centos-stream-x86_64", {"centos-stream-8-x86_64"}),
            ("centos-stream-8", {"centos-stream-8-x86_64"}),
            ("centos-stream-8-x86_64", {"centos-stream-8-x86_64"}),
            ("fedora-stable", {"fedora-31-x86_64", "fedora-32-x86_64"}),
            ("fedora-development", {"fedora-33-x86_64", "fedora-rawhide-x86_64"}),
            ("fedora-29-x86_64", {"fedora-29-x86_64"}),
            ("fedora-29-aarch64", {"fedora-29-aarch64"}),
            ("fedora-29-i386", {"fedora-29-i386"}),
            (
                "fedora-stable-aarch64",
                {"fedora-31-aarch64", "fedora-32-aarch64"},
            ),
            (
                "fedora-development-aarch64",
                {"fedora-33-aarch64", "fedora-rawhide-aarch64"},
            ),
            (
                "fedora-all",
                {
                    "fedora-29-x86_64",
                    "fedora-30-x86_64",
                    "fedora-31-x86_64",
                    "fedora-32-x86_64",
                    "fedora-33-x86_64",
                    "fedora-rawhide-x86_64",
                },
            ),
            (
                "opensuse-leap-all",
                {
                    "opensuse-leap-15.5-x86_64",
                    "opensuse-leap-15.4-x86_64",
                    "opensuse-leap-15.3-x86_64",
                },
            ),
            (
                "opensuse-all",
                {
                    "opensuse-tumbleweed-x86_64",
                    "opensuse-leap-15.5-x86_64",
                    "opensuse-leap-15.4-x86_64",
                    "opensuse-leap-15.3-x86_64",
                },
            ),
            ("opensuse-leap-15.5-aarch64", {"opensuse-leap-15.5-aarch64"}),
            ("opensuse-tumbleweed-ppc64le", {"opensuse-tumbleweed-ppc64le"}),
        ],
    )
    def test_get_build_targets(self, name, targets, mock_get_aliases):
        assert get_build_targets(name) == targets

    def test_get_build_targets_without_default(self):
        assert get_build_targets(default="") == set()

    @pytest.mark.parametrize(
        "names,versions",
        [
            (
                ["fedora-30", "fedora-stable"],
                {"fedora-30-x86_64", "fedora-31-x86_64", "fedora-32-x86_64"},
            ),
            (
                ["fedora-31", "fedora-stable"],
                {"fedora-31-x86_64", "fedora-32-x86_64"},
            ),
        ],
    )
    def test_get_build_targets_from_multiple_values(self, names, versions):
        assert get_build_targets(*names) == versions


@pytest.mark.usefixtures("mock_get_aliases")
class TestGetBranches:
    @pytest.mark.parametrize(
        "name,default_dg_branch,branches",
        [
            ("fedora-29", None, {"f29"}),
            ("fedora-rawhide", None, {"main"}),
            ("fedora-rawhide", "main", {"main"}),
            ("fedora-rawhide", "master", {"master"}),
            ("rawhide", None, {"main"}),
            ("rawhide", "main", {"main"}),
            ("rawhide", "master", {"master"}),
            ("main", None, {"main"}),
            ("master", None, {"master"}),
            ("f30", None, {"f30"}),
            ("fedora-development", None, {"f33", "main"}),
            ("fedora-development", "main", {"f33", "main"}),
            ("fedora-development", "master", {"f33", "master"}),
            ("fedora-stable", None, {"f31", "f32"}),
            ("epel-7", None, {"epel7"}),
            ("epel7", None, {"epel7"}),
            ("el6", None, {"el6"}),
            ("epel-6", None, {"el6"}),
            ("fedora-all", None, {"f29", "f30", "f31", "f32", "f33", "main"}),
            ("fedora-all", "main", {"f29", "f30", "f31", "f32", "f33", "main"}),
            ("fedora-all", "master", {"f29", "f30", "f31", "f32", "f33", "master"}),
        ],
    )
    def test_get_branches(self, name, default_dg_branch, branches):
        if default_dg_branch:
            assert get_branches(name, default_dg_branch=default_dg_branch) == branches
        else:
            assert get_branches(name) == branches

    @pytest.mark.parametrize(
        "names,versions",
        [
            (["fedora-30", "fedora-stable"], {"f30", "f31", "f32"}),
            (["fedora-31", "fedora-stable"], {"f31", "f32"}),
        ],
    )
    def test_get_branches_from_multiple_values(self, names, versions):
        assert get_branches(*names) == versions

    @pytest.mark.parametrize(
        "names,versions",
        [
            (
                {
                    "fedora-30": {"fast_forward_merge_into": ["f31"]},
                    "fedora-stable": {},
                },
                {"f30", "f31", "f32"},
            ),
        ],
    )
    def test_get_branches_from_multiple_values_in_dict(self, names, versions):
        assert get_branches(*names) == versions

    def test_get_branches_without_default(self):
        assert get_branches(default=None) == set()

    @pytest.mark.parametrize(
        "config,branches,ff_branches",
        [
            (
                CommonPackageConfig(
                    dist_git_branches={
                        "rawhide": {"fast_forward_merge_into": ["f30"]},
                        "f31": {},
                        "f32": {},
                    },
                ),
                {"main", "f31", "f32"},
                {"rawhide": {"f30"}, "main": {"f30"}, "f31": set(), "f32": set()},
            ),
            (
                CommonPackageConfig(
                    # no sense but possible!
                    dist_git_branches={
                        "fedora-stable": {
                            "fast_forward_merge_into": ["fedora-stable"],
                        },
                    },
                ),
                {"f31", "f32"},
                {"f31": {"f31", "f32"}, "f32": {"f31", "f32"}},
            ),
        ],
    )
    def test_get_fast_forward_merge_branches_for(
        self,
        config,
        branches,
        ff_branches,
    ):
        assert branches == get_branches(*config.dist_git_branches)
        for source_branch in get_branches(*config.dist_git_branches, with_aliases=True):
            assert (
                get_fast_forward_merge_branches_for(
                    config.dist_git_branches,
                    source_branch,
                )
                == ff_branches[source_branch]
            )


@pytest.mark.usefixtures("mock_get_aliases")
class TestGetKojiTargets:
    @pytest.mark.parametrize("target", ALL_KOJI_TARGETS_SNAPSHOT)
    def test_preserve_koji_targets_single(self, target):
        assert {target} == get_koji_targets(target)

    def test_preserve_all_koji_targets_together(self):
        assert set(ALL_KOJI_TARGETS_SNAPSHOT) == get_koji_targets(
            *ALL_KOJI_TARGETS_SNAPSHOT,
        )

    @pytest.mark.parametrize(
        "name,targets",
        [
            ("fedora-29", {"f29"}),
            ("fedora-rawhide", {"rawhide"}),
            ("rawhide", {"rawhide"}),
            ("master", {"master"}),
            ("f30", {"f30"}),
            ("fedora-development", {"f33", "rawhide"}),
            ("fedora-stable", {"f31", "f32"}),
            ("epel-7", {"epel7"}),
            ("epel7", {"epel7"}),
            ("el6", {"epel6"}),
            ("epel-6", {"epel6"}),
            ("fedora-all", {"f29", "f30", "f31", "f32", "f33", "rawhide"}),
            ("epel-all", {"epel6", "epel7", "epel8", "epel9", "epel10.0", "epel10"}),
        ],
    )
    def test_get_koji_targets(self, name, targets, mock_get_aliases):
        assert get_koji_targets(name) == targets

    def test_get_koji_targets_without_default(self):
        assert get_koji_targets(default=None) == set()


class TestGetAllKojiTargets:
    def test_get_all_koji_targets(self):
        targets = get_all_koji_targets()
        assert targets
        assert "Name" not in targets
        assert "rawhide" in targets
        assert "epel8" in targets
        assert all(isinstance(target, str) for target in targets)


class TestGetAliases:
    @pytest.mark.parametrize(
        "distro_aliases, expected_return",
        [
            pytest.param(
                {
                    "fedora-all": [
                        flexmock(namever="fedora-32"),
                        flexmock(namever="fedora-33"),
                        flexmock(namever="fedora-34"),
                        flexmock(namever="fedora-rawhide"),
                    ],
                    "fedora-stable": [
                        flexmock(namever="fedora-32"),
                        flexmock(namever="fedora-33"),
                    ],
                    "fedora-development": [
                        flexmock(namever="fedora-34"),
                        flexmock(namever="fedora-rawhide"),
                    ],
                    "fedora-latest": [flexmock(namever="fedora-34")],
                    "fedora-latest-stable": [flexmock(namever="fedora-33")],
                    "fedora-branched": [
                        flexmock(namever="fedora-32"),
                        flexmock(namever="fedora-33"),
                        flexmock(namever="fedora-34"),
                    ],
                    "epel-all": [flexmock(namever="epel-8")],
                },
                {
                    "fedora-all": [
                        "fedora-32",
                        "fedora-33",
                        "fedora-34",
                        "fedora-rawhide",
                    ],
                    "fedora-stable": ["fedora-32", "fedora-33"],
                    "fedora-development": ["fedora-34", "fedora-rawhide"],
                    "fedora-latest": ["fedora-34"],
                    "fedora-latest-stable": ["fedora-33"],
                    "fedora-branched": ["fedora-32", "fedora-33", "fedora-34"],
                    "epel-all": ["epel-8"],
                },
                id="after_branching",
            ),
            pytest.param(
                {
                    "fedora-all": [
                        flexmock(namever="fedora-32"),
                        flexmock(namever="fedora-33"),
                        flexmock(namever="fedora-34"),
                        flexmock(namever="fedora-rawhide"),
                    ],
                    "fedora-stable": [
                        flexmock(namever="fedora-32"),
                        flexmock(namever="fedora-33"),
                        flexmock(namever="fedora-34"),
                    ],
                    "fedora-development": [flexmock(namever="fedora-rawhide")],
                    "fedora-latest": [flexmock(namever="fedora-34")],
                    "fedora-latest-stable": [flexmock(namever="fedora-34")],
                    "fedora-branched": [
                        flexmock(namever="fedora-32"),
                        flexmock(namever="fedora-33"),
                        flexmock(namever="fedora-34"),
                    ],
                    "epel-all": [flexmock(namever="epel-8")],
                },
                {
                    "fedora-all": [
                        "fedora-32",
                        "fedora-33",
                        "fedora-34",
                        "fedora-rawhide",
                    ],
                    "fedora-stable": ["fedora-32", "fedora-33", "fedora-34"],
                    "fedora-development": ["fedora-rawhide"],
                    "fedora-latest": ["fedora-34"],
                    "fedora-latest-stable": ["fedora-34"],
                    "fedora-branched": ["fedora-32", "fedora-33", "fedora-34"],
                    "epel-all": ["epel-8"],
                },
                id="after_release",
            ),
            pytest.param(
                {
                    "fedora-all": [
                        flexmock(namever="fedora-33"),
                        flexmock(namever="fedora-34"),
                        flexmock(namever="fedora-rawhide"),
                    ],
                    "fedora-stable": [
                        flexmock(namever="fedora-33"),
                        flexmock(namever="fedora-34"),
                    ],
                    "fedora-development": [flexmock(namever="fedora-rawhide")],
                    "fedora-latest": [flexmock(namever="fedora-34")],
                    "fedora-latest-stable": [flexmock(namever="fedora-34")],
                    "fedora-branched": [
                        flexmock(namever="fedora-33"),
                        flexmock(namever="fedora-34"),
                    ],
                    "epel-all": [flexmock(namever="epel-8")],
                },
                {
                    "fedora-all": [
                        "fedora-33",
                        "fedora-34",
                        "fedora-rawhide",
                    ],
                    "fedora-stable": ["fedora-33", "fedora-34"],
                    "fedora-development": ["fedora-rawhide"],
                    "fedora-latest": ["fedora-34"],
                    "fedora-latest-stable": ["fedora-34"],
                    "fedora-branched": ["fedora-33", "fedora-34"],
                    "epel-all": ["epel-8"],
                },
                id="after_eol",
            ),
        ],
    )
    def test_get_aliases(self, distro_aliases, expected_return):
        flexmock(aliases).should_receive("get_distro_aliases").and_return(
            distro_aliases,
        )
        flexmock(opensuse_distro_aliases).should_receive(
            "get_distro_aliases",
        ).and_return({})

        get_aliases.cache_clear()
        aliases_result = get_aliases()

        assert Counter(d.namever for d in aliases_result["fedora-stable"]) == Counter(
            expected_return["fedora-stable"],
        )
        assert Counter(
            d.namever for d in aliases_result["fedora-development"]
        ) == Counter(
            expected_return["fedora-development"],
        )
        assert Counter(d.namever for d in aliases_result["fedora-all"]) == Counter(
            expected_return["fedora-all"],
        )
        assert Counter(d.namever for d in aliases_result["fedora-latest"]) == Counter(
            expected_return["fedora-latest"],
        )
        assert Counter(
            d.namever for d in aliases_result["fedora-latest-stable"]
        ) == Counter(
            expected_return["fedora-latest-stable"],
        )
        assert Counter(d.namever for d in aliases_result["fedora-branched"]) == Counter(
            expected_return["fedora-branched"],
        )
        assert Counter(d.namever for d in aliases_result["epel-all"]) == Counter(
            expected_return["epel-all"],
        )


@pytest.mark.parametrize(
    "targets, chroots, expected_result",
    [
        pytest.param(["f1", "f2"], ["f1", "f2"], {"f1", "f2"}, id="identical"),
        pytest.param(["f1", "f2"], ["f2", "f3"], {"f2"}, id="some_common"),
        pytest.param(["f1", "f2"], ["f3", "f4"], set(), id="none_common"),
        pytest.param([], ["f1", "f2"], set(), id="one_empty"),
        pytest.param([], [], set(), id="both_empty"),
    ],
)
def test_get_valid_build_targets(targets, chroots, expected_result):
    copr_helper = CoprHelper(flexmock())
    flexmock(Client).should_receive("create_from_config_file")
    flexmock(packit.config.aliases).should_receive("get_build_targets").and_return(
        targets,
    )
    flexmock(CoprHelper).should_receive("get_available_chroots").and_return(chroots)

    assert copr_helper.get_valid_build_targets(*targets) == expected_result


@pytest.mark.parametrize(
    "name, default",
    [
        pytest.param(["f1", "f2"], {"default": "test"}, id="name_set-default_set"),
        pytest.param(["f1", "f2"], {"default": "None"}, id="name_set-default_None"),
        pytest.param([], {"default": "test"}, id="name_None-default_set"),
        pytest.param([], {"default": None}, id="name_None-default_None"),
    ],
)
def test_get_valid_build_targets_get_aliases_call(name, default):
    flexmock(packit.config.aliases).should_receive("get_build_targets").with_args(
        *name,
        **default,
    ).and_return(set())
    flexmock(CoprHelper).should_receive("get_available_chroots").and_return(set())
    CoprHelper(flexmock()).get_valid_build_targets(*name, **default)
