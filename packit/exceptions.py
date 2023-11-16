# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from typing import Any, Union


def ensure_str(inp: Union[bytes, str]) -> str:
    """decode bytes on input or just return the string"""
    # yes, this func doesn't have anything to do with exceptions
    # but it needs to be placed in a leaf module
    # utils import from exceptions hence it can't be there
    return inp if isinstance(inp, str) else inp.decode()


class PackitException(Exception):
    pass


class PackitCommandFailedError(PackitException):
    """A command failed"""

    def __init__(
        self,
        *args,
        stdout_output: Union[str, bytes],
        stderr_output: Union[str, bytes],
    ):
        super().__init__(*args)
        self.stdout_output = ensure_str(stdout_output)
        self.stderr_output = ensure_str(stderr_output)


class PackitConfigException(PackitException):
    pass


class PackitMissingConfigException(PackitConfigException):
    pass


class PackitCoprException(PackitException):
    pass


class PackitCoprProjectException(PackitCoprException):
    pass


class PackitCoprSettingsException(PackitException):
    """
    Raised when we can't edit the Copr project settings.

    Contains the info about fields that we want to edit.
    """

    def __init__(
        self,
        *args: object,
        fields_to_change: dict[str, tuple[Any, Any]],
    ) -> None:
        self.fields_to_change = fields_to_change
        super().__init__(*args)


class PackitInvalidConfigException(PackitConfigException):
    """provided configuration file is not valid"""


class PackitSRPMException(PackitException):
    """Problem with the SRPM"""


class PackitMergeException(PackitException):
    """Failed to merge PR into base branch"""


class PackitDownloadFailedException(PackitException):
    """Failed to download file"""


class PackitLookasideCacheException(PackitException):
    """Problem with lookaside cache"""


class PackitSRPMNotFoundException(PackitSRPMException):
    """SRPM created but not found"""


class PackitFailedToCreateSRPMException(PackitSRPMException):
    """Failed to create SRPM"""


class PackitRPMException(PackitException):
    """Problem with the RPM"""


class PackitRPMNotFoundException(PackitRPMException):
    """RPM created but not found"""


class PackitFailedToCreateRPMException(PackitRPMException):
    """Failed to create RPM"""


class PackitGitException(PackitException):
    """Operation with a git repo failed"""


class PackitNotAGitRepoException(PackitGitException):
    """Target directory is not a git repository as we expected"""


class PackitBodhiException(PackitException):
    """There was a problem while interacting with Bodhi"""


class ImageBuilderError(PackitException):
    """An error happened during the Image Builder interaction"""

    def __init__(self, errors):
        self.errors = errors


class ReleaseSkippedPackitException(PackitException):
    """The release of the new version has been skipped due to a failing check"""
