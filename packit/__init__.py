# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import contextlib
from importlib.metadata import PackageNotFoundError, version

with contextlib.suppress(PackageNotFoundError):
    __version__ = version("packitos")
