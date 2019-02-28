import os

import click
import requests

from packit.local_project import LocalProject


class LocalProjectParameter(click.ParamType):
    """
    Path or url.
    """

    name = "repo"

    def convert(self, value, param, ctx):
        try:
            if os.path.isdir(value):
                return LocalProject(working_dir=value)

            try:
                res = requests.get(value)
                if res.ok:
                    return LocalProject(git_url=value)
                self.fail("Cannot connect to specified url.", param, ctx)
            except requests.exceptions.BaseHTTPError as ex:
                self.fail("Cannot connect to specified url.", param, ctx)

        except ValueError as ex:
            self.fail(ex, param, ctx)
