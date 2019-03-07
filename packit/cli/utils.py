import functools
import logging
import sys

import click

from packit.exceptions import PackitException

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
                    func(config, *args, **kwargs)
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
