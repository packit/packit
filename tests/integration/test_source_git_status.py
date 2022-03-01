# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.exceptions import PackitException


def test_source_git_status_no_trailers(
    sourcegit_and_remote, distgit_and_remote, api_instance_source_git
):
    """Check that an error is thrown if no trailers are present."""
    with pytest.raises(PackitException):
        api_instance_source_git.sync_status()
