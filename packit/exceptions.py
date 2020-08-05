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

from typing import Union, Any, Tuple, Dict

from deprecated import deprecated


def ensure_str(inp: Union[bytes, str]) -> str:
    """ decode bytes on input or just return the string """
    # yes, this func doesn't have anything to do with exceptions
    # but it needs to be placed in a leaf module
    # utils import from exceptions hence it can't be there
    return inp if isinstance(inp, str) else inp.decode()


class PackitException(Exception):
    pass


class PackitCommandFailedError(PackitException):
    """ A command failed """

    def __init__(
        self,
        *args,
        stdout_output: Union[str, bytes] = None,
        stderr_output: Union[str, bytes] = None,
    ):
        super().__init__(*args)
        self.stdout_output = ensure_str(stdout_output)
        self.stderr_output = ensure_str(stderr_output)


class PackitConfigException(PackitException):
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
        self, *args: object, fields_to_change: Dict[str, Tuple[Any, Any]]
    ) -> None:
        self.fields_to_change = fields_to_change
        super().__init__(*args)


class PackitInvalidConfigException(PackitConfigException):
    """ provided configuration file is not valid """


@deprecated(reason="Use the PackitFailedToCreateSRPMException instead.")
class FailedCreateSRPM(PackitException):
    """ Failed to create SRPM """


class PackitSRPMException(PackitException):
    """ Problem with the SRPM """


class PackitSRPMNotFoundException(PackitSRPMException):
    """ SRPM created but not found """


class PackitFailedToCreateSRPMException(PackitSRPMException):
    """ Failed to create SRPM """


class PackitRPMException(PackitException):
    """ Problem with the RPM """


class PackitRPMNotFoundException(PackitRPMException):
    """ RPM created but not found """


class PackitFailedToCreateRPMException(PackitRPMException):
    """ Failed to create RPM """
