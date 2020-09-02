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

import pytest
from flexmock import flexmock
from gnupg import GPG
from packit.exceptions import PackitException

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
        # good signature, key present
        ("a", "G", ["a"], ["a"], True, 0),
        # bad signature, key present
        ("a", "B", ["a"], ["a"], False, 0),
        # good signature, key not allowed
        ("a", "G", ["c", "d"], ["c", "d"], False, 0),
        # bad signature, key not present
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
    gpg_flexmock.should_receive("recv_keys").and_return(
        flexmock(fingerprints=["fingerprint"])
    ).times(download_times)

    repo_mock = flexmock(
        git=flexmock()
        .should_receive("show")
        .and_return(sign)
        .and_return(key)
        .and_return(sign)
        .mock()
    )

    verifier = CommitVerifier()
    is_valid = verifier.check_signature_of_commit(
        commit=flexmock(hexsha="abcd", repo=repo_mock),
        possible_key_fingerprints=allowed_keys,
    )
    assert is_valid == valid


@pytest.mark.parametrize(
    "key,"
    "first_sign,"
    "second_sign,"
    "allowed_keys,"
    "local_keys,"
    "local_keys_after_download,"
    "valid,"
    "download_times",
    [
        # no signature
        (None, "N", None, [], [], None, False, 0),
        # key not present but downloaded
        ("a", "E", "G", ["a"], [], ["a"], True, 1),
        # key not present, all need to be downloaded before getting the signer
        ("a", "E", "G", ["a", "b", "c", "d"], [], ["a", "b", "c", "d"], True, 4),
        # key downloaded but signature is bad
        ("a", "E", "B", ["a"], [], ["a"], False, 1),
    ],
)
def test_check_signature_of_commit_not_present_key(
    key,
    first_sign,
    second_sign,
    allowed_keys,
    local_keys,
    local_keys_after_download,
    valid,
    download_times,
):
    gpg_flexmock = flexmock(GPG)
    gpg_flexmock.should_receive("list_keys").and_return(
        flexmock(fingerprints=local_keys)
    )

    gpg_flexmock.should_receive("recv_keys").and_return(
        flexmock(fingerprints=["fingerprint"])
    ).times(download_times)

    repo_mock = flexmock(
        git=flexmock()
        .should_receive("show")
        .and_return(first_sign)
        .and_return(key)
        .and_return(second_sign)
        .mock()
    )

    verifier = CommitVerifier()
    is_valid = verifier.check_signature_of_commit(
        commit=flexmock(hexsha="abcd", repo=repo_mock),
        possible_key_fingerprints=allowed_keys,
    )
    assert is_valid == valid


def test_check_signature_of_commit_key_not_found():
    gpg_flexmock = flexmock(GPG)

    # No key present
    gpg_flexmock.should_receive("list_keys").and_return(flexmock(fingerprints=[]))

    # No key received
    gpg_flexmock.should_receive("recv_keys").and_return(flexmock(fingerprints=[]))

    # Signature cannot be checked
    repo_mock = flexmock(git=flexmock().should_receive("show").and_return("E").mock())

    verifier = CommitVerifier()
    with pytest.raises(PackitException) as ex:
        verifier.check_signature_of_commit(
            commit=flexmock(hexsha="abcd", repo=repo_mock),
            possible_key_fingerprints=["a"],
        )
    assert "Cannot receive" in str(ex)


# This could possibly but unlikely fail if all the default key servers are down.
@pytest.mark.parametrize(
    "keyid, ok",
    [
        (
            "A3E9A812AAB73DA7",
            True,
        ),
        (
            "NOTEXISTING",
            False,
        ),
    ],  # Jirka's key id
)
def test_download_gpg_key_if_needed(keyid, ok):
    cf = CommitVerifier()
    if ok:
        assert cf.download_gpg_key_if_needed(keyid)
    else:
        with pytest.raises(PackitException):
            cf.download_gpg_key_if_needed(keyid)
