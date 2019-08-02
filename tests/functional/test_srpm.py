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

"""
Functional tests for srpm comand
"""

from tests.spellbook import call_real_packit


def test_srpm_command(upstream_instance):
    u, ups = upstream_instance
    call_real_packit(parameters=["--debug", "srpm"], cwd=u)
    assert list(u.glob("*.src.rpm"))[0].exists()


def test_srpm_custom_path(upstream_instance):
    u, ups = upstream_instance
    custom_path = "sooooorc.rpm"
    call_real_packit(parameters=["--debug", "srpm", "--output", custom_path], cwd=u)
    assert u.joinpath(custom_path).is_file()


def test_srpm_twice_with_custom_name(upstream_instance):
    u, ups = upstream_instance
    custom_path = "sooooorc.rpm"
    call_real_packit(parameters=["--debug", "srpm", "--output", custom_path], cwd=u)
    assert u.joinpath(custom_path).is_file()

    custom_path2 = "sooooorc2.rpm"
    call_real_packit(parameters=["--debug", "srpm", "--output", custom_path2], cwd=u)
    assert u.joinpath(custom_path2).is_file()


def test_srpm_twice(upstream_instance):
    u, ups = upstream_instance
    call_real_packit(parameters=["--debug", "srpm"], cwd=u)
    call_real_packit(parameters=["--debug", "srpm"], cwd=u)

    srpm_files = list(u.glob("*.src.rpm"))
    assert len(srpm_files) == 2

    srpm1, srpm2 = srpm_files
    name1, name2 = "beer-0.1.0-2", "beer-0.1.0-3"
    assert srpm1.name.startswith(name1) or srpm2.name.startswith(name1)
    assert srpm1.name.startswith(name2) or srpm2.name.startswith(name2)
