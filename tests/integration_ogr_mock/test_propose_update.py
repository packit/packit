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
Functional tests for propose-update command
"""
import os
from packit.api import PackitAPI
from tests.integration_ogr_mock.test_status import PackitUnittestOgr


class ProposeUpdate(PackitUnittestOgr):
    datafile_github = "TestPropose_github.yaml"
    datafile_pagure = "TestPropose_pagure.yaml"

    def setUp(self):
        super().setUp()
        self.api = PackitAPI(
            config=self.conf, package_config=self.pc, upstream_local_project=self.lp
        )
        self.api._up = self.upstream
        self.api._dg = self.dg

    def test_propose_update(self):
        # change specfile little bit to have there some change
        specfile_location = os.path.join(self.lp.working_dir, "python-ogr.spec")
        with open(specfile_location, "a") as myfile:
            myfile.write("# test text")

        self.api.sync_release("master")
