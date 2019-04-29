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

import pytest
from flexmock import flexmock
from gnupg import GPG

from packit.security import (
    CommitSignatureStatus,
    VALID_SIGNATURE_STATUSES,
    CommitVerifier,
)


@pytest.mark.parametrize(
    "sign,status",
    [
        ("N", CommitSignatureStatus.no_signature),
        ("B", CommitSignatureStatus.bad),
        ("G", CommitSignatureStatus.good_valid),
        ("U", CommitSignatureStatus.good_unknown_validity),
    ],
)
def test_commit_signature_status(sign, status):
    """Just to be sure we do not mess anything in the future."""
    assert status == CommitSignatureStatus(sign)


@pytest.mark.parametrize(
    "sign,status",
    [
        ("N", CommitSignatureStatus.no_signature),
        ("B", CommitSignatureStatus.bad),
        ("G", CommitSignatureStatus.good_valid),
        ("U", CommitSignatureStatus.good_unknown_validity),
    ],
)
def test_get_commit_signature_status(sign, status):
    """Just to be sure we do not mess anything in the future."""
    repo_mock = flexmock(git=flexmock().should_receive("show").and_return(sign).mock())

    status_found = CommitVerifier.get_commit_signature_status(
        commit=flexmock(hexsha="abcd", repo=repo_mock)
    )
    assert status_found == status


@pytest.mark.parametrize(
    "status,valid",
    [
        (CommitSignatureStatus.no_signature, False),
        (CommitSignatureStatus.bad, False),
        (CommitSignatureStatus.good_valid, True),
        (CommitSignatureStatus.good_unknown_validity, True),
    ],
)
def test_commit_signature_status_validity(status, valid):
    """Just to be sure we do not mess anything in the future."""
    is_valid = status in VALID_SIGNATURE_STATUSES
    assert is_valid == valid


@pytest.mark.parametrize(
    "key,sign,allowed_keys,local_keys,valid,download_times",
    [
        ("a", "G", ["a"], ["a"], True, 0),
        ("a", "B", ["a"], ["a"], False, 0),
        ("a", "G", ["c", "d"], ["c", "d"], False, 0),
        ("a", "G", ["a"], ["b", "c"], True, 1),
        ("a", "B", ["c"], [], False, 0),
    ],
)
def test_check_signature_of_commit(
    key, sign, allowed_keys, local_keys, valid, download_times
):
    gpg_flexmock = flexmock(GPG)
    gpg_flexmock.should_receive("list_keys").and_return(
        flexmock(fingerprints=local_keys)
    )
    gpg_flexmock.should_receive("recv_keys").times(download_times)
    repo_mock = flexmock(
        git=flexmock().should_receive("show").and_return(key).and_return(sign).mock()
    )

    verifier = CommitVerifier()
    is_valid = verifier.check_signature_of_commit(
        commit=flexmock(hexsha="abcd", repo=repo_mock),
        possible_key_fingerprints=allowed_keys,
    )
    assert is_valid == valid
