import sys

import pytest
from flexmock import flexmock

from packit.cli.utils import cover_packit_exception
from packit.exceptions import PackitException


def test_cover_packit_exception_decorator():
    flexmock(sys).should_receive("exit")

    @cover_packit_exception
    def covered_func():
        raise PackitException("Test exception")

    covered_func()


def test_cover_packit_exception_decorator_exit_code():
    flexmock(sys).should_receive("exit").with_args(5)

    @cover_packit_exception(exit_code=5)
    def covered_func():
        raise PackitException("Test exception")

    covered_func()


def test_cover_packit_exception_decorator_config_debug_false():
    flexmock(sys).should_receive("exit")

    @cover_packit_exception
    def covered_func(config=None):
        raise PackitException("Test exception")

    covered_func(config=flexmock(debug=False))


def test_cover_packit_exception_decorator_config_debug_true():
    flexmock(sys).should_receive("exit").times(0)

    @cover_packit_exception
    def covered_func(config=None):
        raise PackitException("Test exception")

    with pytest.raises(PackitException):
        covered_func(config=flexmock(debug=True))


def test_cover_packit_exception_decorator_other_exception():
    flexmock(sys).should_receive("exit")

    class CustomException(Exception):
        pass

    @cover_packit_exception
    def covered_func(config=None):
        raise CustomException("Other test exception")

    with pytest.raises(CustomException):
        covered_func()


def test_cover_packit_exception_decorator_other_exception_config_debug():
    flexmock(sys).should_receive("exit")

    class CustomException(Exception):
        pass

    @cover_packit_exception
    def covered_func(config=None):
        raise CustomException("Other test exception")

    with pytest.raises(CustomException):
        covered_func(config=flexmock(debug=True))
