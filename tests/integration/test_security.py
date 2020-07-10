# MIT License
#
# Copyright (c) 2018 Red Hat, Inc.

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

from packit.api import PackitAPI
from packit.exceptions import PackitException
from packit.security import CommitVerifier
from tests.integration.utils import remove_gpg_key_pair


def test_allowed_gpg_keys_none(api_instance_source_git: PackitAPI):
    api_instance_source_git.up.allowed_gpg_keys = None
    flexmock(CommitVerifier).should_receive("check_signature_of_commit").times(0)
    api_instance_source_git.up.check_last_commit()


@pytest.mark.parametrize("allowed_gpg_keys", [[], ["abcd", "efgh"]])
def test_allowed_gpg_keys_not_allowed(
    allowed_gpg_keys, api_instance_source_git: PackitAPI, gnupg_key_fingerprint: str
):
    api_instance_source_git.up.local_project.git_repo.git.commit(
        message="signed commit", gpg_sign=gnupg_key_fingerprint, allow_empty=True
    )

    api_instance_source_git.up.allowed_gpg_keys = allowed_gpg_keys
    with pytest.raises(PackitException) as ex:
        api_instance_source_git.up.check_last_commit()
    assert "not signed" in str(ex)


def test_allowed_gpg_keys_allowed(
    api_instance_source_git: PackitAPI, gnupg_key_fingerprint: str
):
    api_instance_source_git.up.local_project.git_repo.git.commit(
        message="signed commit", gpg_sign=gnupg_key_fingerprint, allow_empty=True
    )

    api_instance_source_git.up.allowed_gpg_keys = [gnupg_key_fingerprint]
    api_instance_source_git.up.check_last_commit()


def test_allowed_gpg_keys_not_existing_key(
    api_instance_source_git: PackitAPI, gnupg_instance: GPG, gnupg_key_fingerprint: str
):
    api_instance_source_git.up.local_project.git_repo.git.commit(
        message="signed commit", gpg_sign=gnupg_key_fingerprint, allow_empty=True
    )
    remove_gpg_key_pair(
        gpg_binary=gnupg_instance.gpgbinary, fingerprint=gnupg_key_fingerprint
    )
    api_instance_source_git.up.allowed_gpg_keys = [gnupg_key_fingerprint]
    with pytest.raises(PackitException) as ex:
        api_instance_source_git.up.check_last_commit()
    assert "Cannot receive a gpg key" in str(ex)
