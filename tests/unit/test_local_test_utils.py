# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path
from unittest.mock import patch

from packit.utils.local_test_utils import LocalTestUtils


class TestBuildTmtCmd:
    """Test cases for _build_tmt_cmd function"""

    def test_basic_command_structure(self):
        """Test basic command structure without plans"""
        rpm_paths = [Path("/path/to/package1.rpm"), Path("/path/to/package2.rpm")]
        target = "fedora:41"
        plans = None

        result = LocalTestUtils._build_tmt_cmd(rpm_paths, target, plans)

        expected_base = [
            "tmt",
            "-c",
            "initiator=packit",
            "run",
            "discover",
            "--how",
            "fmf",
            "provision",
            "--how",
            "container",
            "--image",
            "fedora:41",
            "prepare",
            "--how",
            "install",
        ]

        assert result[: len(expected_base)] == expected_base
        assert result[-2:] == ["execute", "report"]

    def test_with_single_plan(self):
        """Test command with single plan specified"""
        rpm_paths = [Path("/path/to/package.rpm")]
        target = "centos:8"
        plans = ["basic-tests"]

        result = LocalTestUtils._build_tmt_cmd(rpm_paths, target, plans)

        assert "plan" in result
        assert "--name=basic-tests" in result
        # Check plan comes after "run" and before "discover"
        run_index = result.index("run")
        discover_index = result.index("discover")
        plan_index = result.index("plan")
        assert run_index < plan_index < discover_index

    def test_with_multiple_plans(self):
        """Test command with multiple plans specified"""
        rpm_paths = [Path("/path/to/package.rpm")]
        target = "ubuntu:22.04"
        plans = ["unit-tests", "integration-tests", "smoke-tests"]

        result = LocalTestUtils._build_tmt_cmd(rpm_paths, target, plans)

        for plan in plans:
            assert f"--name={plan}" in result

        plan_count = result.count("plan")
        assert plan_count == len(plans)

    def test_empty_plans_list(self):
        """Test command with empty plans list"""
        rpm_paths = [Path("/path/to/package.rpm")]
        target = "fedora:40"
        plans = []

        result = LocalTestUtils._build_tmt_cmd(rpm_paths, target, plans)

        assert "plan" not in result
        assert "--name=" not in " ".join(result)

    @patch("os.path.abspath")
    def test_rpm_paths_conversion(self, mock_abspath):
        """Test that RPM paths are converted to absolute paths"""
        mock_abspath.side_effect = lambda x: f"/absolute{x}"

        rpm_paths = [Path("relative/path1.rpm"), Path("relative/path2.rpm")]
        target = "fedora:39"
        plans = None

        result = LocalTestUtils._build_tmt_cmd(rpm_paths, target, plans)

        assert mock_abspath.call_count == len(rpm_paths)

        assert "--package" in result
        assert "/absoluterelative/path1.rpm" in result
        assert "/absoluterelative/path2.rpm" in result

    def test_single_rpm_path(self):
        """Test command with single RPM path"""
        rpm_paths = [Path("/single/package.rpm")]
        target = "rhel:9"
        plans = None

        with patch("os.path.abspath", return_value="/single/package.rpm"):
            result = LocalTestUtils._build_tmt_cmd(rpm_paths, target, plans)

        package_count = result.count("--package")
        assert package_count == 1
        assert "/single/package.rpm" in result

    def test_multiple_rpm_paths(self):
        """Test command with multiple RPM paths"""
        rpm_paths = [
            Path("/path/pkg1.rpm"),
            Path("/path/pkg2.rpm"),
            Path("/path/pkg3.rpm"),
        ]
        target = "fedora:38"
        plans = ["test-plan"]

        with patch("os.path.abspath", side_effect=lambda x: str(x)):
            result = LocalTestUtils._build_tmt_cmd(rpm_paths, target, plans)

        package_count = result.count("--package")
        assert package_count == len(rpm_paths)

        for rpm in rpm_paths:
            assert str(rpm) in result

    def test_different_target_formats(self):
        """Test command with different target formats"""
        rpm_paths = [Path("/test.rpm")]
        plans = None

        test_targets = ["fedora:41", "centos:stream9", "ubuntu:22.04", "rhel:8.5"]

        for target in test_targets:
            with patch("os.path.abspath", return_value="/test.rpm"):
                result = LocalTestUtils._build_tmt_cmd(rpm_paths, target, plans)

            assert "--image" in result
            image_index = result.index("--image")
            assert result[image_index + 1] == target


class TestTmtTargetToMockRoot:
    """Test cases for tmt_target_to_mock_root function"""

    def test_standard_fedora_target(self):
        """Test conversion of standard Fedora target"""
        result = LocalTestUtils.tmt_target_to_mock_root("fedora:41")
        assert result == "fedora-41-x86_64"

    def test_standard_centos_target(self):
        """Test conversion of standard CentOS target"""
        result = LocalTestUtils.tmt_target_to_mock_root("centos:8")
        assert result == "centos-8-x86_64"

    def test_rhel_target(self):
        """Test conversion of RHEL target"""
        result = LocalTestUtils.tmt_target_to_mock_root("rhel:9")
        assert result == "rhel-9-x86_64"

    def test_fedora_rawhide(self):
        """Test conversion of Fedora rawhide target"""
        result = LocalTestUtils.tmt_target_to_mock_root("fedora:rawhide")
        assert result == "fedora-rawhide-x86_64"

    def test_centos_stream(self):
        """Test conversion of CentOS Stream target"""
        result = LocalTestUtils.tmt_target_to_mock_root("centos:stream9")
        assert result == "centos-stream9-x86_64"

    def test_ubuntu_target(self):
        """Test conversion of Ubuntu target"""
        result = LocalTestUtils.tmt_target_to_mock_root("ubuntu:22.04")
        assert result == "ubuntu-22.04-x86_64"

    def test_invalid_target_no_colon(self):
        """Test handling of invalid target without colon"""
        result = LocalTestUtils.tmt_target_to_mock_root("fedora41")
        assert result == "default"

    def test_invalid_target_empty_string(self):
        """Test handling of empty target string"""
        result = LocalTestUtils.tmt_target_to_mock_root("")
        assert result == "default"

    def test_target_with_empty_version(self):
        """Test target with empty version part"""
        result = LocalTestUtils.tmt_target_to_mock_root("fedora:")
        assert result == "fedora--x86_64"

    def test_target_with_empty_distro(self):
        """Test target with empty distro part"""
        result = LocalTestUtils.tmt_target_to_mock_root(":41")
        assert result == "-41-x86_64"
