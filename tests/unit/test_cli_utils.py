# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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
