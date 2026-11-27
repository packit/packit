# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from copr.v3.exceptions import CoprRequestException
from flexmock import flexmock

import packit
from packit.copr_helper import _MAX_PROJECT_EDIT_RETRIES, CoprHelper


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


class TestCoprProjectEditRetry:
    """Tests for the retry logic in create_or_update_copr_project
    when concurrent tasks cause chroot conflicts."""

    @staticmethod
    def _make_copr_helper():
        project_proxy_mock = flexmock()
        copr_client_mock = flexmock(
            config={"copr_url": "https://fedoracloud.org"},
            project_proxy=project_proxy_mock,
            project_chroot_proxy=flexmock(),
        )
        flexmock(packit.copr_helper.CoprClient).should_receive(
            "create_from_config_file",
        ).and_return(copr_client_mock)

        upstream_mock = flexmock(git_url="https://github.com/test/test.git")
        copr_helper = CoprHelper(upstream_mock)
        return copr_helper, project_proxy_mock

    @staticmethod
    def _make_project_mock(**chroot_repos):
        return flexmock(
            chroot_repos=chroot_repos,
            description="test",
            unlisted_on_hp=True,
            delete_after_days=60,
            additional_repos=[],
            runtime_dependencies=[],
            module_hotfixes=False,
            bootstrap="default",
        )

    def test_project_edit_retries_on_chroot_conflict(self):
        copr_helper, project_proxy = self._make_copr_helper()

        # Stale snapshot: missing centos chroot added by a concurrent task
        project_stale = self._make_project_mock(
            **{"fedora-rawhide-x86_64": "http://repo/fedora-rawhide-x86_64"},
        )
        # Fresh re-read: now includes centos (added by concurrent task),
        # but still missing fedora-44 (the chroot we need to add)
        project_fresh = self._make_project_mock(
            **{
                "fedora-rawhide-x86_64": "http://repo/fedora-rawhide-x86_64",
                "centos-stream-10-x86_64": "http://repo/centos-stream-10-x86_64",
            },
        )

        project_proxy.should_receive("add").and_return(project_stale).once()
        project_proxy.should_receive("get").and_return(
            project_stale,
        ).and_return(project_fresh).twice()

        project_proxy.should_receive("edit").and_raise(
            CoprRequestException(
                "Can't drop chroot from project, related build 123 is still in progress",
            ),
        ).and_return(None).twice()

        flexmock(packit.copr_helper.time).should_receive("sleep").once()

        copr_helper.create_or_update_copr_project(
            project="test-project",
            chroots=["fedora-rawhide-x86_64", "fedora-44-x86_64"],
            owner="packit",
        )

    def test_project_edit_raises_after_max_retries(self):
        copr_helper, project_proxy = self._make_copr_helper()

        project_mock = self._make_project_mock(
            **{"fedora-rawhide-x86_64": "http://repo/fedora-rawhide-x86_64"},
        )

        project_proxy.should_receive("add").and_return(project_mock).once()
        project_proxy.should_receive("get").and_return(
            project_mock,
        ).times(_MAX_PROJECT_EDIT_RETRIES)

        project_proxy.should_receive("edit").and_raise(
            CoprRequestException(
                "Can't drop chroot from project, related build 123 is still in progress",
            ),
        ).times(_MAX_PROJECT_EDIT_RETRIES)

        flexmock(packit.copr_helper.time).should_receive("sleep").times(
            _MAX_PROJECT_EDIT_RETRIES - 1,
        )

        with pytest.raises(CoprRequestException, match="Can't drop chroot"):
            copr_helper.create_or_update_copr_project(
                project="test-project",
                chroots=["fedora-rawhide-x86_64", "fedora-44-x86_64"],
                owner="packit",
            )

    def test_project_edit_does_not_retry_other_errors(self):
        copr_helper, project_proxy = self._make_copr_helper()

        project_mock = self._make_project_mock(
            **{"fedora-rawhide-x86_64": "http://repo/fedora-rawhide-x86_64"},
        )

        project_proxy.should_receive("add").and_return(project_mock).once()
        project_proxy.should_receive("get").and_return(project_mock).once()

        project_proxy.should_receive("edit").and_raise(
            CoprRequestException("Unable to connect to Copr"),
        ).once()

        flexmock(packit.copr_helper.time).should_receive("sleep").never()

        with pytest.raises(CoprRequestException, match="Unable to connect"):
            copr_helper.create_or_update_copr_project(
                project="test-project",
                chroots=["fedora-rawhide-x86_64", "fedora-44-x86_64"],
                owner="packit",
            )
