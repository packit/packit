import inspect
import os
from contextlib import contextmanager

from rebasehelper.specfile import SpecFile


@contextmanager
def cwd(target):
    """
    Manage cwd in a pushd/popd fashion.

    Usage:

        with cwd(tmpdir):
          do something in tmpdir
    """
    curdir = os.getcwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(curdir)


def get_specfile(path: str) -> SpecFile:
    s = inspect.signature(SpecFile)
    if "changelog_entry" in s.parameters:
        return SpecFile(path=path, changelog_entry=None)
    else:
        return SpecFile(path=path)
