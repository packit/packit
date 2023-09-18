# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
This module contains code related to security, signing and verification.
"""

import logging
from enum import Enum
from typing import Optional

import git
from gnupg import GPG, ListKeys

from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


class CommitVerifier:
    """
    Class used for verifying git commits. Uses python-gnupg for accessing the GPG binary.
    """

    def __init__(self, key_server: Optional[str] = None) -> None:
        """
        :param key_server: GPG key server to be used
        """
        self._gpg: Optional[GPG] = None
        if key_server:
            self.key_servers = [key_server]
        else:
            self.key_servers = [
                "keyserver.ubuntu.com",
                "keys.openpgp.org",
                "pgp.surf.nl",
                # "pgp.mit.edu",  # slow & unreliable
            ]

    @property
    def gpg(self) -> GPG:
        """
        gnupg.GPG instance from python-gnupg
        """
        if not self._gpg:
            self._gpg = GPG()
        return self._gpg

    @property
    def _gpg_keys(self) -> ListKeys:
        """
        List of installed gpg keys

        (do not cache this value)
        """
        return self.gpg.list_keys()

    @property
    def _gpg_fingerprints(self) -> list[str]:
        """List of fingerprints of the saved keys"""
        return self._gpg_keys.fingerprints

    def download_gpg_key_if_needed(self, key_fingerprint: str) -> str:
        """
        Download the gpg key from the self.key_servers if it is not present.

        :param key_fingerprint: fingerprint of the gpg key
        """
        if key_fingerprint in self._gpg_fingerprints:
            return key_fingerprint

        try:
            for keyserver in self.key_servers:
                logger.debug(f"Downloading {key_fingerprint!r} from {keyserver!r}.")
                result = self.gpg.recv_keys(keyserver, key_fingerprint)
                if result.fingerprints:
                    return result.fingerprints[0]
        except Exception as ex:
            raise PackitException(
                f"Cannot receive a gpg key: {key_fingerprint}",
            ) from ex

        raise PackitException(f"Cannot receive a gpg key: {key_fingerprint}")

    def check_signature_of_commit(
        self,
        commit: git.Commit,
        possible_key_fingerprints: list[str],
    ) -> bool:
        """
        Check the validity of the commit signature
        and test if the signer is present in the provided list.
        (Commit without signature returns False.)
        """
        status = self.get_commit_signature_status(commit=commit)
        if status == CommitSignatureStatus.no_signature:
            logger.debug("Commit not signed.")
            return False

        if status == CommitSignatureStatus.cannot_be_checked:
            # We need to download keys before getting the signer
            for key in possible_key_fingerprints:
                self.download_gpg_key_if_needed(key_fingerprint=key)

        signer = self.get_commit_signer_fingerprint(commit)

        if not signer:
            logger.debug("Cannot get a signer of the commit.")
            return False

        if signer not in possible_key_fingerprints:
            logger.warning("Signature author not authorized.")
            return False

        is_valid = self.is_commit_signature_valid(commit)
        if not is_valid:
            logger.warning(f"Commit {commit.hexsha!r} signature is not valid.")
        return is_valid

    def is_commit_signature_valid(self, commit: git.Commit) -> bool:
        """
        Check the validity of the commit signature.
        Key needs to be already present.
        """
        commit_status = self.get_commit_signature_status(commit)
        if commit_status in VALID_SIGNATURE_STATUSES:
            logger.debug(f"Commit {commit.hexsha!r} signature is valid.")
            return True

        logger.warning(f"Commit {commit.hexsha!r} signature is not valid.")
        return False

    @staticmethod
    def get_commit_signature_status(commit: git.Commit) -> "CommitSignatureStatus":
        """Get a signature status from the given commit."""
        signature_mark = CommitVerifier._get_commit_info(commit, pretty_format="%G?")
        return CommitSignatureStatus(signature_mark)

    @staticmethod
    def get_commit_signer_fingerprint(commit: git.Commit) -> str:
        """Get a signer fingerprint from the given commit"""
        return CommitVerifier._get_commit_info(commit, pretty_format="%GF")

    @staticmethod
    def _get_commit_info(commit: git.Commit, pretty_format: str) -> str:
        """
        Return a commit information in a given format.

        See `git show --help` and `--pretty=format` for more information.
        """
        try:
            return commit.repo.git.show(commit.hexsha, pretty=f"format:{pretty_format}")
        except git.GitCommandError as error:
            raise PackitException(
                f"Cannot find commit {commit.hexsha!r} to check its signature.",
            ) from error


class CommitSignatureStatus(Enum):
    no_signature = "N"
    bad = "B"
    good_valid = "G"
    good_unknown_validity = "U"
    good_expired = "X"
    good_made_by_expired_key = "Y"
    good_made_by_revoked_key = "R"
    cannot_be_checked = "E"


VALID_SIGNATURE_STATUSES = [
    CommitSignatureStatus.good_valid,
    CommitSignatureStatus.good_unknown_validity,
]
