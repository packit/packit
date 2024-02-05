# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
from typing import Optional


class LabelRequirementsConfig:
    """Configuration of requirements on label."""

    def __init__(
        self,
        present: Optional[list] = None,
        absent: Optional[list] = None,
    ):
        self.present = present or []
        self.absent = absent or []


class RequirementsConfig:
    """Configuration of requirements."""

    def __init__(self, label: Optional[LabelRequirementsConfig] = None):
        self.label = label or LabelRequirementsConfig()
