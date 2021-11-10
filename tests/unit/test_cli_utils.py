# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import sys

from flexmock import flexmock

from packit.cli.utils import cover_packit_exception
from packit.exceptions import PackitException


def test_cover_packit_exception_decorator():
    flexmock(sys).should_receive("exit")

    @cover_packit_exception
    def covered_func():
        raise PackitException("Test exception")

    covered_func()


def test_cover_packit_exception_decorator_attribute():
    flexmock(sys).should_receive("exit")

    @cover_packit_exception
    def covered_func(attribute):
        assert attribute
        raise PackitException("Other test exception")

    covered_func(attribute=flexmock())


def test_cover_packit_exception_decorator_exit_code_default():
    flexmock(sys).should_receive("exit").with_args(2)

    @cover_packit_exception()
    def covered_func():
        raise PackitException("Test exception")

    covered_func()


def test_cover_packit_exception_decorator_exit_code_keyboard_interrupt():
    flexmock(sys).should_receive("exit").with_args(1)

    @cover_packit_exception()
    def covered_func():
        raise KeyboardInterrupt("Test keyboard interrupt")

    covered_func()


def test_cover_packit_exception_decorator_exit_code_other_exception():
    flexmock(sys).should_receive("exit").with_args(4)

    class CustomException(Exception):
        pass

    @cover_packit_exception()
    def covered_func():
        raise CustomException("Test keyboard interrupt")

    covered_func()


def test_cover_packit_exception_decorator_exit_code_other_exception_override():
    flexmock(sys).should_receive("exit").with_args(5)

    class CustomException(Exception):
        pass

    @cover_packit_exception(exit_code=5)
    def covered_func():
        raise CustomException("Test keyboard interrupt")

    covered_func()


def test_cover_packit_exception_decorator_exit_code_override():
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
    flexmock(sys).should_receive("exit")

    @cover_packit_exception
    def covered_func(config=None):
        raise PackitException("Test exception")

    covered_func(config=flexmock(debug=True))


def test_cover_packit_exception_decorator_other_exception():
    flexmock(sys).should_receive("exit").with_args(4)

    class CustomException(Exception):
        pass

    @cover_packit_exception
    def covered_func():
        raise CustomException("Other test exception")

    covered_func()


def test_cover_packit_exception_decorator_other_exception_config_debug():
    flexmock(sys).should_receive("exit")

    class CustomException(Exception):
        pass

    @cover_packit_exception
    def covered_func(config=None):
        raise CustomException("Other test exception")

    covered_func(config=flexmock(debug=True))
