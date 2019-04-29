import inspect

from rebasehelper.specfile import SpecFile


def get_specfile(path: str) -> SpecFile:
    s = inspect.signature(SpecFile)
    if "changelog_entry" in s.parameters:
        return SpecFile(path=path, changelog_entry=None)
    else:
        return SpecFile(path=path)
