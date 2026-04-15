# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
import requests
from flexmock import flexmock

from packit.utils.release_monitoring import (
    MonitoringMetadata,
    get_monitoring_metadata,
)


@pytest.fixture
def mock_project():
    return flexmock(repo="test-package")


class TestGetMonitoringMetadata:
    def test_monitoring_toml(self, mock_project):
        mock_project.should_receive("get_file_content").with_args(
            "monitoring.toml",
            ref="rawhide",
        ).and_return("monitoring = true\n" "scratch_build = false\n").once()

        result = get_monitoring_metadata(mock_project)

        assert result == MonitoringMetadata(
            monitoring=True,
            bugzilla=True,
            all_versions=False,
            stable_only=False,
            scratch_build=False,
        )

    def test_monitoring_toml_all_fields(self, mock_project):
        mock_project.should_receive("get_file_content").with_args(
            "monitoring.toml",
            ref="rawhide",
        ).and_return(
            "monitoring = true\n"
            "bugzilla = false\n"
            "all_versions = true\n"
            "stable_only = false\n"
            "scratch_build = true\n",
        ).once()

        result = get_monitoring_metadata(mock_project)

        assert result == MonitoringMetadata(
            monitoring=True,
            bugzilla=False,
            all_versions=True,
            stable_only=False,
            scratch_build=True,
        )

    def test_monitoring_toml_defaults(self, mock_project):
        mock_project.should_receive("get_file_content").with_args(
            "monitoring.toml",
            ref="rawhide",
        ).and_return("").once()

        result = get_monitoring_metadata(mock_project)

        assert result == MonitoringMetadata(
            monitoring=False,
            bugzilla=True,
            all_versions=False,
            stable_only=False,
            scratch_build=False,
        )

    @pytest.mark.parametrize(
        "status,expected",
        [
            (
                "no-monitoring",
                MonitoringMetadata(
                    monitoring=False,
                    bugzilla=False,
                    all_versions=False,
                    stable_only=False,
                    scratch_build=False,
                ),
            ),
            (
                "monitoring",
                MonitoringMetadata(
                    monitoring=True,
                    bugzilla=True,
                    all_versions=False,
                    stable_only=False,
                    scratch_build=False,
                ),
            ),
            (
                "monitoring-with-scratch",
                MonitoringMetadata(
                    monitoring=True,
                    bugzilla=True,
                    all_versions=False,
                    stable_only=False,
                    scratch_build=True,
                ),
            ),
            (
                "monitoring-all",
                MonitoringMetadata(
                    monitoring=True,
                    bugzilla=True,
                    all_versions=True,
                    stable_only=False,
                    scratch_build=False,
                ),
            ),
            (
                "monitoring-all-scratch",
                MonitoringMetadata(
                    monitoring=True,
                    bugzilla=True,
                    all_versions=True,
                    stable_only=False,
                    scratch_build=True,
                ),
            ),
            (
                "monitoring-stable",
                MonitoringMetadata(
                    monitoring=True,
                    bugzilla=True,
                    all_versions=False,
                    stable_only=True,
                    scratch_build=False,
                ),
            ),
            (
                "monitoring-stable-scratch",
                MonitoringMetadata(
                    monitoring=True,
                    bugzilla=True,
                    all_versions=False,
                    stable_only=True,
                    scratch_build=True,
                ),
            ),
        ],
    )
    def test_legacy_api_fallback(self, mock_project, status, expected):
        mock_project.should_receive("get_file_content").and_raise(FileNotFoundError)

        response = flexmock(
            json=lambda: {"monitoring": status},
            raise_for_status=lambda: None,
        )
        flexmock(requests).should_receive("get").and_return(response).once()

        result = get_monitoring_metadata(mock_project)

        assert result == expected

    def test_legacy_api_unknown_status(self, mock_project):
        mock_project.should_receive("get_file_content").and_raise(FileNotFoundError)

        response = flexmock(
            json=lambda: {"monitoring": "unknown-status"},
            raise_for_status=lambda: None,
        )
        flexmock(requests).should_receive("get").and_return(response).once()

        result = get_monitoring_metadata(mock_project)

        assert result is None

    def test_legacy_api_request_error(self, mock_project):
        mock_project.should_receive("get_file_content").and_raise(FileNotFoundError)

        flexmock(requests).should_receive("get").and_raise(
            requests.exceptions.ConnectionError("connection failed"),
        )

        result = get_monitoring_metadata(mock_project)

        assert result is None

    def test_monitoring_toml_error_falls_back_to_legacy(self, mock_project):
        mock_project.should_receive("get_file_content").and_raise(
            RuntimeError("unexpected error"),
        )

        response = flexmock(
            json=lambda: {"monitoring": "monitoring"},
            raise_for_status=lambda: None,
        )
        flexmock(requests).should_receive("get").and_return(response).once()

        result = get_monitoring_metadata(mock_project)

        assert result == MonitoringMetadata(
            monitoring=True,
            bugzilla=True,
            all_versions=False,
            stable_only=False,
            scratch_build=False,
        )

    def test_package_name_creates_project(self):
        mock_project = flexmock(repo="test-package")
        mock_project.should_receive("get_file_content").with_args(
            "monitoring.toml",
            ref="rawhide",
        ).and_return("monitoring = true\n").once()

        mock_service = flexmock()
        mock_service.should_receive("get_project").with_args(
            repo="test-package",
            namespace="rpms",
        ).and_return(mock_project).once()

        flexmock(
            __name__="ogr.services.pagure",
        )
        from packit.utils import release_monitoring

        flexmock(release_monitoring).should_receive("PagureService").and_return(
            mock_service,
        ).once()

        result = get_monitoring_metadata("test-package")

        assert result.monitoring is True
