# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os
import re
from pathlib import Path
from typing import (
    Optional,
)

logger = logging.getLogger(__name__)


class LocalTestUtils:
    @staticmethod
    def _build_tmt_cmd(
        rpm_paths: list[Path],
        target: str,
        plans: Optional[list[str]],
    ) -> list[str]:
        """
        Build base tmt command to be sent to tmt.
        Args:
            rpm_paths: List of paths to local RPMs to install
            target: Target container image (e.g. 'fedora:41')
            run_all: Whether to run all plans (currently unused)
            plans: Optional list of TMT plan names to run

        Returns:
            List of command-line arguments for the `tmt` command
        """
        cmd = [
            "tmt",
            "-c",
            "initiator=packit",
            "run",
        ]

        if plans:
            for plan in plans:
                cmd += ["plan", f"--name={plan}"]

        cmd += [
            "discover",
            "--how",
            "fmf",
            "provision",
            "--how",
            "container",
            "--image",
            target,
            "prepare",
            "--how",
            "install",
        ]

        for rpm in rpm_paths:
            cmd += ["--package", os.path.abspath(rpm)]

        cmd += ["execute", "report"]
        return cmd

    @staticmethod
    def tmt_target_to_mock_root(target: str) -> str:
        """
        Convert TMT target format
        (e.g., 'fedora:rawhide') to mock root name (e.g., 'fedora-rawhide-x86_64')
        """
        try:
            distro, version = target.split(":")
        except ValueError:
            return "default"
        return f"{distro}-{version}-x86_64"

    @staticmethod
    def parse_tmt_response(stdout: str) -> tuple[int, int]:
        """
        Parse the TMT command stdout and extract the number of executed and passed tests.

        Args:
            stdout: The standard output from a `tmt run` command

        Returns:
            A tuple (executed, passed) representing test counts
        """
        executed_match = re.search(r"summary:\s+(\d+)\s+test[s]?\s+executed", stdout)
        passed_match = re.search(r"summary:\s+(\d+)\s+test[s]?\s+passed", stdout)

        executed = int(executed_match.group(1)) if executed_match else 0
        passed = int(passed_match.group(1)) if passed_match else 0

        return executed, passed
