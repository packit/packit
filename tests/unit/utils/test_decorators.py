# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.utils.decorators import fallback_return_value


class TestFallbackReturnValue:
    @pytest.mark.parametrize(
        "raise_exception, decorator_exceptions",
        [
            pytest.param(ValueError, ValueError, id="raised"),
            pytest.param(ValueError, KeyError, id="raised"),
        ],
    )
    def test_fallback_return_value(self, raise_exception, decorator_exceptions):
        fallback_value = "test_fallback_value"

        @fallback_return_value(fallback_value, exceptions=decorator_exceptions)
        def simple_function(exc=None):
            """Simple test function."""
            if exc is not None:
                raise exc
            return 42

        # `except` accepts both single exception or tuple of exceptions, to make testing easier
        # we will transform also single exception to tuple
        decorator_exceptions = (
            decorator_exceptions
            if isinstance(decorator_exceptions, tuple)
            else (decorator_exceptions,)
        )

        if raise_exception:
            if raise_exception in decorator_exceptions:
                assert simple_function(raise_exception) == fallback_value
            elif raise_exception not in decorator_exceptions:
                with pytest.raises(raise_exception):
                    simple_function(raise_exception)

        elif not raise_exception:
            assert simple_function() == 42
