import functools
import sys

from packit.exceptions import PackitException


def cover_packit_exception(_func=None, *, exit_code=1):
    """
    Decorator for executing the function in the try-except block.

    The PackitException is caught and
    - raised in debug
    - sys.exit(exit_code), otherwise

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
            except PackitException:
                if config and config.debug:
                    raise
                sys.exit(exit_code)

        return covered_func

    if _func is None:
        return decorator_cover
    else:
        return decorator_cover(_func)
