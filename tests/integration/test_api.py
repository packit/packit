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

"""    custom_path = "sooooorc.rpm"
Functional tests for srpm comand
"""
from pathlib import Path
import os
import flexmock
from subprocess import check_output
import unittest
from packit.api import PackitAPI
from tests.integration.testbase import PackitUnittestOgr


class ProposeUpdate(PackitUnittestOgr):
    def setUp(self):
        super().setUp()
        self.api = PackitAPI(
            config=self.conf, package_config=self.pc, upstream_local_project=self.lp
        )
        self.api._up = self.upstream
        self.api._dg = self.dg
        # Do not upload package, because no credentials given in CI
        flexmock(self.api).should_receive("_handle_sources").and_return(None)
        self.set_git_user()

    @unittest.skip(
        "Issue in ogr causing that User is not stored in persistent yaml files for pagure"
    )
    def test_propose_update(self):
        # change specfile little bit to have there some change
        specfile_location = os.path.join(self.lp.working_dir, "python-ogr.spec")
        with open(specfile_location, "a") as myfile:
            myfile.write("# test text")
        check_output(
            f"cd {self.lp.working_dir}; git commit -m 'test change' python-ogr.spec",
            shell=True,
        )
        self.api.sync_release("master")


def test_srpm(api_instance):
    u, d, api = api_instance
    api.create_srpm()
    assert list(Path.cwd().glob("*.src.rpm"))[0].exists()


def test_srpm_custom_path(api_instance):
    u, d, api = api_instance
    custom_path = "sooooorc.rpm"
    api.create_srpm(output_file=custom_path)
    assert Path.cwd().joinpath(custom_path).is_file()
