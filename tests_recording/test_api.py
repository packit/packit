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
from subprocess import check_output

import rebasehelper
from flexmock import flexmock
from rebasehelper.exceptions import RebaseHelperError
from requre.cassette import DataTypes

from packit.api import PackitAPI
from tests_recording.testbase import PackitUnittestOgr


@unittest.skip("Not working yet")
class ProposeUpdate(PackitUnittestOgr):
    def setUp(self):
        if (
            hasattr(rebasehelper, "VERSION")
            and int(rebasehelper.VERSION.split(".")[1]) >= 19
        ):
            self.cassette.data_miner.key = "rebase-helper>=0.19"
        else:
            self.cassette.data_miner.key = "rebase-helper<0.19"
        self.cassette.data_miner.data_type = DataTypes.Dict

        super().setUp()
        self.api = PackitAPI(
            config=self.conf, package_config=self.pc, upstream_local_project=self.lp
        )
        self.api._up = self.upstream
        self.api._dg = self.dg
        self.set_git_user()

    def check_version_increase(self):
        # change specfile little bit to have there some change
        specfile_location = self.lp.working_dir / "python-ogr.spec"
        filedata = specfile_location.read_text()
        # Patch the specfile with new version
        version_increase = "0.0.0"
        for line in filedata.splitlines():
            if "Version:" in line:
                version = line.rsplit(" ", 1)[1]
                v1, v2, v3 = version.split(".")
                version_increase = ".".join([v1, str(int(v2) + 1), v3])
                filedata = filedata.replace(version, version_increase)
                break
        specfile_location.write_text(filedata)
        check_output(
            f"cd {self.lp.working_dir};"
            f"git commit -m 'test change' python-ogr.spec;"
            f"git tag -a {version_increase} -m 'my version {version_increase}'",
            shell=True,
        )
        self.api.sync_release("master")

    def test_comment_in_spec(self):
        """
        change specfile little bit to have there some change, do not increase version
        """
        specfile_location = self.lp.working_dir / "python-ogr.spec"
        with specfile_location.open("a") as myfile:
            myfile.write("\n# comment\n")
        version_increase = "10.0.0"
        check_output(
            f"cd {self.lp.working_dir};"
            f"git commit -m 'test change' python-ogr.spec;"
            f"git tag -a {version_increase} -m 'my version {version_increase}'",
            shell=True,
        )
        self.api.sync_release("master")

    @unittest.skipIf(
        hasattr(rebasehelper, "VERSION")
        and int(rebasehelper.VERSION.split(".")[1]) >= 19,
        "Older version of rebasehelper raised exception",
    )
    def test_version_change_exception(self):
        """
        check if it raises exception, because sources are not uploaded in distgit
        Downgrade rebasehelper to version < 0.19.0
        """
        self.assertRaises(RebaseHelperError, self.check_version_increase)

    @unittest.skipUnless(
        hasattr(rebasehelper, "VERSION")
        and int(rebasehelper.VERSION.split(".")[1]) >= 19,
        "New version of rebasehelper works without raised exception",
    )
    def test_version_change_new_rebaseheler(self):
        """
        check if it not raises exception, because sources are not uploaded in distgit
        """
        self.check_version_increase()

    def test_version_change_mocked(self):
        """
        version is not not uploaded, so skip in this test
        """
        flexmock(self.api).should_receive("_handle_sources").and_return(None)
        self.check_version_increase()
