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

from packit.utils.commands import cwd

from tests.spellbook import call_packit


def test_generate_pass(upstream_without_config):
    with cwd(upstream_without_config):
        assert not (upstream_without_config / ".packit.yaml").is_file()

        # This test requires packit on pythonpath
        result = call_packit(parameters=["generate"])

        assert result.exit_code == 0

        assert (upstream_without_config / ".packit.yaml").is_file()


def test_generate_fail(cwd_upstream_or_distgit):
    result = call_packit(
        parameters=["generate"], working_dir=str(cwd_upstream_or_distgit)
    )

    assert result.exit_code == 2  # packit config already exists --force needed
