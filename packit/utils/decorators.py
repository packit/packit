# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import contextlib
import functools
import logging
from typing import Any, Callable, Optional, Union

logger = logging.getLogger(__name__)


def fallback_return_value(
    fallback_value: Any,
    exceptions: Union[type[Exception], tuple[type[Exception]]] = Exception,
    callback: Optional[Callable] = None,
) -> Any:
    """
    The function of this decorator is to return some fallback value in case an exception was raised
    during a function call.

    :param fallback_value: a value which will be returned if a specified exception was raised
    :param exceptions: exception(s) which should be handled, by default all exceptions are caught
    :param callback: function to call if fallback happens
    :return: func original return value if no exception was raised
            fallback_return_value if a specified exception was caught
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def inner(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                logger.warning(
                    f"Fallback return value used while calling {func.__name__} because of "
                    f"{type(e).__name__}"
                    f"{': ' + str(e) if str(e) else ''} ",
                )
                if callback is not None:
                    with contextlib.suppress(Exception):
                        callback()
                return fallback_value

        return inner

    return decorator
