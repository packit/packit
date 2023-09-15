# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

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
    allowed_gpg_keys,
    api_instance_source_git: PackitAPI,
    gnupg_key_fingerprint: str,
):
    api_instance_source_git.up.local_project.git_repo.git.commit(
        message="signed commit",
        gpg_sign=gnupg_key_fingerprint,
        allow_empty=True,
    )

    api_instance_source_git.up.allowed_gpg_keys = allowed_gpg_keys
    with pytest.raises(PackitException) as ex:
        api_instance_source_git.up.check_last_commit()
    assert "not signed" in str(ex)


def test_allowed_gpg_keys_allowed(
    api_instance_source_git: PackitAPI,
    gnupg_key_fingerprint: str,
):
    api_instance_source_git.up.local_project.git_repo.git.commit(
        message="signed commit",
        gpg_sign=gnupg_key_fingerprint,
        allow_empty=True,
    )

    api_instance_source_git.up.allowed_gpg_keys = [gnupg_key_fingerprint]
    api_instance_source_git.up.check_last_commit()


def test_allowed_gpg_keys_not_existing_key(
    api_instance_source_git: PackitAPI,
    gnupg_instance: GPG,
    gnupg_key_fingerprint: str,
):
    api_instance_source_git.up.local_project.git_repo.git.commit(
        message="signed commit",
        gpg_sign=gnupg_key_fingerprint,
        allow_empty=True,
    )
    remove_gpg_key_pair(
        gpg_binary=gnupg_instance.gpgbinary,
        fingerprint=gnupg_key_fingerprint,
    )
    api_instance_source_git.up.allowed_gpg_keys = [gnupg_key_fingerprint]
    with pytest.raises(PackitException) as ex:
        api_instance_source_git.up.check_last_commit()
    assert "Cannot receive a gpg key" in str(ex)
