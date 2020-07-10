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

import unittest

import pkg_resources

from packit.status import Status
from requre.cassette import DataTypes
from tests_recording.testbase import PackitUnittestOgr


@unittest.skip("Not working yet")
class TestStatus(PackitUnittestOgr):
    def setUp(self):
        super().setUp()
        self.cassette.data_miner.key = (
            f'github-{pkg_resources.get_distribution("PyGithub").version}'
        )
        self.cassette.data_miner.data_type = DataTypes.Dict
        self.status = Status(self.conf, self.pc, self.upstream, self.dg)

    def test_status(self):
        assert self.status

    def test_distgen_versions(self):
        table = self.status.get_dg_versions()
        assert table
        assert len(table) >= 3

    def test_koji_builds(self):
        table = self.status.get_koji_builds()
        assert table
        assert len(table) >= 2

    def test_copr_builds(self):
        table = self.status.get_copr_builds()
        assert table
        assert len(table) >= 2

    def test_updates(self):
        table = self.status.get_updates()
        assert table
        assert len(table) >= 3

        # Check if get_updates doesn't return more than one stable update per branch
        stable_branches = []
        for [update, _, status] in table:
            branch = update[-4:]
            if status == "stable":
                stable_branches.append(branch)
        assert len(set(stable_branches)) == len(stable_branches)

    @unittest.skip("The replaying does not work.")
    def test_up_releases(self):
        table = self.status.get_up_releases()
        assert len(table) >= 5

    def test_dowstream_pr(self):
        table = self.status.get_downstream_prs()
        assert len(table) >= 0
