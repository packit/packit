import functools
import logging
from typing import Union, Tuple, Type, Any, Callable

logger = logging.getLogger(__name__)


def fallback_return_value(
    fallback_value: Any,
    exceptions: Union[Type[Exception], Tuple[Type[Exception]]] = Exception,
) -> Any:
    """
    The function of this decorator is to return some fallback value in case an exception was raised
    during a function call.

    :param fallback_value: a value which will be returned if a specified exception was raised
    :param exceptions: exception(s) which should be handled, by default all exceptions are caught
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
                    f"{': ' + str(e) if str(e) else ''} "
                )
                return fallback_value

        return inner

    return decorator
