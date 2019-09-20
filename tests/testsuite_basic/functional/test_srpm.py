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

from tests.testsuite_basic.spellbook import call_real_packit, build_srpm


def test_srpm_command(upstream_instance):
    u, ups = upstream_instance
    call_real_packit(parameters=["--debug", "srpm"], cwd=u)
    srpm_path = list(u.glob("*.src.rpm"))[0]
    assert srpm_path.exists()
    build_srpm(srpm_path)


def test_srpm_custom_path(upstream_instance):
    u, ups = upstream_instance
    custom_path = "sooooorc.rpm"
    call_real_packit(parameters=["--debug", "srpm", "--output", custom_path], cwd=u)
    srpm_path = u.joinpath(custom_path)
    assert srpm_path.is_file()
    build_srpm(srpm_path)


def test_srpm_twice_with_custom_name(upstream_instance):
    u, ups = upstream_instance
    custom_path = "sooooorc.rpm"
    call_real_packit(parameters=["--debug", "srpm", "--output", custom_path], cwd=u)
    srpm_path1 = u.joinpath(custom_path)
    assert srpm_path1.is_file()
    build_srpm(srpm_path1)

    custom_path2 = "sooooorc2.rpm"
    call_real_packit(parameters=["--debug", "srpm", "--output", custom_path2], cwd=u)
    srpm_path2 = u.joinpath(custom_path2)
    assert srpm_path2.is_file()
    build_srpm(srpm_path2)


def test_srpm_twice(upstream_instance):
    u, ups = upstream_instance
    call_real_packit(parameters=["--debug", "srpm"], cwd=u)
    call_real_packit(parameters=["--debug", "srpm"], cwd=u)

    # since we build from the 0.1.0, we would get the same SRPM because of '--new 0.1.0'
    srpm_files = list(u.glob("*.src.rpm"))

    assert srpm_files[0].exists()

    build_srpm(srpm_files[0])


def test_srpm_command_using_distgit(upstream_and_remote, distgit_and_remote):
    u, _ = upstream_and_remote
    d, _ = distgit_and_remote
    call_real_packit(parameters=["--debug", "srpm"], cwd=d)
    srpm_path = list(d.glob("*.src.rpm"))[0]
    assert srpm_path.exists()
    build_srpm(srpm_path)
