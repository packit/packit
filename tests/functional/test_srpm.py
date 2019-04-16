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


def test_srpm_upstream_ref_head(upstream_instance):
    u, ups = upstream_instance
    custom_ref = "HEAD"
    call_real_packit(
        parameters=["--debug", "srpm", "--upstream-ref", custom_ref], cwd=u
    )
    assert list(u.glob("*.src.rpm"))[0].exists()


def test_srpm_upstream_ref(upstream_instance_with_two_commits):
    u, ups = upstream_instance_with_two_commits

    custom_ref = "HEAD~"
    call_real_packit(
        parameters=["--debug", "srpm", "--upstream-ref", custom_ref], cwd=u
    )
    assert list(u.glob("*.src.rpm"))[0].exists()


def test_srpm_upstream_ref_commit(upstream_instance_with_two_commits):
    u, ups = upstream_instance_with_two_commits

    custom_ref = ups.local_project.git_repo.commit("HEAD~").hexsha
    call_real_packit(
        parameters=["--debug", "srpm", "--upstream-ref", custom_ref], cwd=u
    )
    assert list(u.glob("*.src.rpm"))[0].exists()


def test_srpm_upstream_ref_branch(upstream_instance_with_two_commits):
    custom_ref = "new_branch"

    u, ups = upstream_instance_with_two_commits
    ups.local_project.git_repo.create_head(custom_ref)

    call_real_packit(
        parameters=["--debug", "srpm", "--upstream-ref", custom_ref], cwd=u
    )
    assert list(u.glob("*.src.rpm"))[0].exists()
