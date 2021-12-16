# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_distribution("packitos").version
except DistributionNotFound:
    # package is not installed
    pass
