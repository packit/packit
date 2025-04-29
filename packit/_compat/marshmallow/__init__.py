# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from importlib.metadata import version

from packaging.version import parse

if parse(version("marshmallow")) < parse("4.0"):
    from marshmallow_enum import EnumField

    USE_MARSHMALLOW_ENUM = True
else:
    from marshmallow.fields import Enum as EnumField

    USE_MARSHMALLOW_ENUM = False

__all__ = ["USE_MARSHMALLOW_ENUM", "EnumField"]
