# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("packitos")
except PackageNotFoundError:
    # package is not installed
    pass
