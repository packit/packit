# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
from typing import Optional


class TestCommandConfig:
    """Configuration of test command."""

    def __init__(
        self,
        default_labels: Optional[list[str]] = None,
        default_identifier: Optional[str] = None,
    ):
        self.default_labels = default_labels
        self.default_identifier = default_identifier
