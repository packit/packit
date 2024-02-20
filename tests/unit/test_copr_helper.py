# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

import packit
from packit.copr_helper import CoprHelper


class TestCoprHelper:
    @pytest.mark.parametrize(
        # copr_client.mock_chroot_proxy.get_list() returns dictionary
        "get_list_keys, expected_return",
        [
            pytest.param(["chroot1", "_chroot2"], ["chroot1"], id="chroot_list"),
            pytest.param([], [], id="empty_list"),
        ],
    )
    def test_get_avilable_chroots(self, get_list_keys, expected_return):
        copr_client_mock = flexmock(mock_chroot_proxy=flexmock())
        copr_client_mock.mock_chroot_proxy.should_receive("get_list.keys").and_return(
            get_list_keys,
        )
        flexmock(packit.copr_helper.CoprClient).should_receive(
            "create_from_config_file",
        ).and_return(copr_client_mock)

        copr_helper = CoprHelper("_upstream_local_project")
        copr_helper.get_available_chroots.cache_clear()

        assert copr_helper.get_available_chroots() == expected_return

    @pytest.mark.parametrize(
        "owner,project,section,expected_suffix",
        [
            (
                "@rhinstaller",
                "Anaconda",
                "permissions",
                "g/rhinstaller/Anaconda/permissions/",
            ),
            ("@rhinstaller", "Anaconda", None, "g/rhinstaller/Anaconda/edit/"),
            ("someone", "Anaconda", "permissions", "someone/Anaconda/permissions/"),
        ],
    )
    def test_settings_url(self, owner, project, section, expected_suffix):
        copr_client_mock = flexmock(config={"copr_url": "https://fedoracloud.org"})

        flexmock(packit.copr_helper.CoprClient).should_receive(
            "create_from_config_file",
        ).and_return(copr_client_mock)
        copr_helper = CoprHelper("_upstream_local_project")

        assert (
            copr_helper.get_copr_settings_url(owner, project, section)
            == f"https://fedoracloud.org/coprs/{expected_suffix}"
        )

    @pytest.mark.parametrize(
        "update_dict,expect_call_args",
        [
            (
                {},
                None,
            ),
            (
                {"fedora-rawhide-x86_64": {"additional_repos": ([], ["y"])}},
                {
                    "additional_repos": ["y"],
                },
            ),
        ],
    )
    def test_update_chroot_specific_configuration(self, update_dict, expect_call_args):
        project_proxy_mock = flexmock()
        copr_client_mock = flexmock(
            config={"copr_url": "https://fedoracloud.org"},
            project_chroot_proxy=project_proxy_mock,
        )

        flexmock(packit.copr_helper.CoprClient).should_receive(
            "create_from_config_file",
        ).and_return(copr_client_mock)

        if expect_call_args:
            project_proxy_mock.should_receive("edit").with_args(
                projectname="project",
                ownername="owner",
                chrootname="fedora-rawhide-x86_64",
                **expect_call_args,
            ).once()

        copr_helper = CoprHelper("_upstream_local_project")
        copr_helper._update_chroot_specific_configuration(
            project="project",
            owner="owner",
            update_dict=update_dict,
        )

    @pytest.mark.parametrize(
        "targets_dict,result_dict",
        [
            ({"fedora-rawhide": {}}, {}),
            ({"fedora-rawhide": {"distros": ["y"]}}, {}),
            (
                {"fedora-rawhide": {"additional_repos": ["y"]}},
                {
                    "fedora-rawhide-x86_64": {"additional_repos": ([], ["y"])},
                },
            ),
            (
                {
                    "fedora-rawhide": {
                        "additional_modules": "httpd:2.4,nodejs:12",
                        "distros": ["z"],
                    },
                },
                {
                    "fedora-rawhide-x86_64": {
                        "additional_modules": ("", "httpd:2.4,nodejs:12"),
                    },
                },
            ),
        ],
    )
    def test_get_chroot_specific_configuration_to_update(
        self,
        targets_dict,
        result_dict,
    ):
        project_proxy_mock = flexmock()
        copr_client_mock = flexmock(
            config={"copr_url": "https://fedoracloud.org"},
            project_chroot_proxy=project_proxy_mock,
        )

        flexmock(packit.copr_helper.CoprClient).should_receive(
            "create_from_config_file",
        ).and_return(copr_client_mock)

        if result_dict:
            project_proxy_mock.should_receive("get").and_return(
                {
                    "additional_modules": "",
                    "additional_packages": [],
                    "additional_repos": [],
                    "comps_name": None,
                    "delete_after_days": None,
                    "isolation": "unchanged",
                    "mock_chroot": "centos-stream-8-x86_64",
                    "ownername": "@theforeman",
                    "projectname": "pr-testing-playground",
                    "with_opts": [],
                    "without_opts": [],
                },
            )

        copr_helper = CoprHelper("_upstream_local_project")
        assert (
            copr_helper._get_chroot_specific_configuration_to_update(
                "project",
                "owner",
                targets_dict=targets_dict,
            )
            == result_dict
        )
