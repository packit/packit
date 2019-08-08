# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import builtins

from pkg_resources import get_distribution, DistributionNotFound


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass

if os.getenv("RECORD_REQUESTS"):
    from packit.session_recording import (
        upgrade_import_system,
        ReplaceType,
        RequestResponseHandling,
        tempfile,
    )

    HANDLE_MODULE_LIST = [
        ("requests", {"who_name": "rebasehelper"}),
        (
            "requests",
            {"who_name": "packit.distgit"},
            {"head": [ReplaceType.DECORATOR, RequestResponseHandling.decorator]},
        ),
        (
            "tempfile",
            {"who_name": "packit.distgit"},
            {"": [ReplaceType.REPLACE, tempfile]},
        ),
    ]

    builtins.__import__ = upgrade_import_system(
        builtins.__import__,
        name_filters=HANDLE_MODULE_LIST,
        debug_file="import_module.log",
    )
