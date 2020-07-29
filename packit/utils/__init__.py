# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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

from packit.utils.commands import run_command, run_command_remote, cwd
from packit.utils.extensions import get_rev_list_kwargs, assert_existence, nested_get
from packit.utils.logging import (
    StreamLogger,
    PackitFormatter,
    set_logging,
    commits_to_nice_str,
)
from packit.utils.repo import (
    is_git_repo,
    get_repo,
    get_namespace_and_repo_name,
    is_a_git_ref,
    git_remote_url_to_https_url,
)
from packit.utils.version import get_packit_version


__all__ = [
    run_command.__name__,
    run_command_remote.__name__,
    cwd.__name__,
    get_rev_list_kwargs.__name__,
    assert_existence.__name__,
    nested_get.__name__,
    StreamLogger.__name__,
    PackitFormatter.__name__,
    set_logging.__name__,
    commits_to_nice_str.__name__,
    is_git_repo.__name__,
    get_repo.__name__,
    get_namespace_and_repo_name.__name__,
    is_a_git_ref.__name__,
    git_remote_url_to_https_url.__name__,
    get_packit_version.__name__,
]
