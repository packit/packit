# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from typing import NamedTuple


class SourcesItem(NamedTuple):
    path: str
    url: str

    def __repr__(self):
        return f"SourcesItem(path={self.path}, url={self.url})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SourcesItem):
            raise NotImplementedError()

        return self.path == other.path and self.url == other.url
