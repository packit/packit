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

"""
This module contains code related to security, signing and verification.
"""

import logging
from enum import Enum
from typing import Optional, List

import git
from gnupg import GPG, ListKeys
from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


class Verifier:
    def __init__(self, key_server: str = None) -> None:
        self._gpg: Optional[GPG] = None
        self.key_server = key_server or "keys.fedoraproject.org"

    @property
    def gpg(self) -> GPG:
        if not self._gpg:
            for gpg_location in ["gpg2", "gpg"]:
                try:
                    self._gpg = GPG(gpgbinary=gpg_location)
                    break
                except FileNotFoundError:
                    continue
            else:
                raise PackitException("GPG binary not found.")
        return self._gpg

    @property
    def _gpg_keys(self) -> ListKeys:
        """
        List of installed gpg keys

        (do not cache this value)
        """
        return self.gpg.list_keys()

    @property
    def _gpg_fingerprints(self) -> str:
        return self._gpg_keys.fingerprints

    def download_gpg_key_if_needed(self, key_fingerprint: str) -> None:
        """
        Download the gpg key from the self.keyserver
        if it is not present.

        :param key_fingerprint: str (fingerprint of the gpg key)
        """
        if key_fingerprint in self._gpg_fingerprints:
            return

        try:
            self.gpg.recv_keys(self.key_server, key_fingerprint)
        except ValueError as error:
            # python-gnupg do not recognise KEY_CONSIDERED response from gpg2
            if "KEY_CONSIDERED" not in str(error):
                raise PackitException(
                    f"Cannot receive a gpg key: {key_fingerprint}", error
                )
        except Exception as ex:
            raise PackitException(f"Cannot receive a gpg key: {key_fingerprint}", ex)

    def check_signature_of_commit(
        self, commit: git.Commit, possible_key_fingerprints: List[str]
    ) -> bool:
        signer = self.get_commit_signer_fingerprint(commit)

        if signer not in possible_key_fingerprints:
            logger.debug("Signature author not authorized.")
            return False

        self.download_gpg_key_if_needed(key_fingerprint=signer)

        return self.is_commit_signature_valid(commit)

    def is_commit_signature_valid(self, commit: git.Commit) -> bool:
        commit_status = self.get_commit_signature_status(commit)
        if commit_status in VALID_SIGNATURE_STATUSES:
            logger.debug(f"Commit '{commit.hexsha}' is valid.")
            return True

        logger.debug(f"Commit '{commit.hexsha}' is not valid.")
        return False

    @staticmethod
    def get_commit_signature_status(commit: git.Commit) -> "CommitSignatureStatus":
        signature_mark = Verifier._get_commit_info(commit, pretty_format="%G?")
        return CommitSignatureStatus(signature_mark)

    @staticmethod
    def get_commit_signer_fingerprint(commit: git.Commit) -> str:
        return Verifier._get_commit_info(commit, pretty_format="%GF")

    @staticmethod
    def _get_commit_info(commit: git.Commit, pretty_format: str) -> str:
        try:
            return commit.repo.git.show(commit.hexsha, pretty=f"format:{pretty_format}")
        except git.GitCommandError as error:
            raise PackitException(
                f"Cannot find a commit '{commit.hexsha}' when checking commit signatures.",
                error,
            )


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
