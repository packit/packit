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

import functools
import logging
import sys

import click

from packit.api import PackitAPI
from packit.config import get_local_package_config, Config
from packit.exceptions import PackitException
from packit.local_project import LocalProject

logger = logging.getLogger(__name__)


def cover_packit_exception(_func=None, *, exit_code=None):
    """
    Decorator for executing the function in the try-except block.

    The PackitException is caught and
    - raised in debug
    - sys.exit(exit_code), otherwise

    On other Exceptions we print the message about creating an issue.


    If the function receives config, it recognises the debug mode.
    => use it after the @pass_config decorator
    """

    def decorator_cover(func):
        @functools.wraps(func)
        def covered_func(config=None, *args, **kwargs):
            try:
                if config:
                    func(config=config, *args, **kwargs)
                else:
                    func(*args, **kwargs)
            except KeyboardInterrupt:
                click.echo("Quitting on user request.")
                sys.exit(1)
            except PackitException as exc:
                if config and config.debug:
                    logger.exception(exc)
                else:
                    logger.error(exc)
                sys.exit(exit_code or 2)
            except Exception as exc:
                if config and config.debug:
                    logger.exception(exc)
                else:
                    logger.error(exc)
                    click.echo(
                        "Unexpected exception occurred,\n"
                        "please fill an issue here:\n"
                        "https://github.com/packit-service/packit/issues",
                        err=True,
                    )
                sys.exit(exit_code or 3)

        return covered_func

    if _func is None:
        return decorator_cover
    else:
        return decorator_cover(_func)


def get_packit_api(
    config: Config, local_project: LocalProject, dist_git_path: str = None
):
    """
    Load the package config, set other options and return the PackitAPI
    """
    package_config = get_local_package_config(
        local_project.working_dir, try_local_dir_first=True
    )

    if dist_git_path:
        package_config.downstream_project_url = dist_git_path
    package_config.upstream_project_url = local_project.working_dir

    api = PackitAPI(
        config=config,
        package_config=package_config,
        upstream_local_project=local_project,
    )
    return api
