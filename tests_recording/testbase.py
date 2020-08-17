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


import shutil
from os import makedirs
from subprocess import check_output, CalledProcessError

from requre.base_testclass import RequreTestCase
from requre.helpers.tempfile import TempFile

import packit.distgit
import packit.upstream
from packit.config import Config, get_package_config_from_repo
from packit.exceptions import PackitException
from packit.local_project import LocalProject

DATA_DIR = "test_data"


class PackitUnittestOgr(RequreTestCase):
    @staticmethod
    def get_test_config():
        try:
            conf = Config.get_user_config()
        except PackitException:
            conf = Config()
        conf.dry_run = True
        return conf

    @staticmethod
    def set_git_user():
        try:
            check_output(["git", "config", "--global", "-l"])
        except CalledProcessError:
            check_output(
                ["git", "config", "--global", "user.email", "test@example.com"]
            )
            check_output(["git", "config", "--global", "user.name", "Tester"])

    def setUp(self):
        super().setUp()
        self.conf = self.get_test_config()
        self.static_tmp = "/tmp/packit_tmp"
        makedirs(self.static_tmp, exist_ok=True)
        TempFile.root = self.static_tmp
        self.project_ogr = self.conf.get_project(url="https://github.com/packit/ogr")

        self.pc = get_package_config_from_repo(project=self.project_ogr, ref="master")
        if not self.pc:
            raise RuntimeError("Package config not found.")
        self.dg = packit.distgit.DistGit(self.conf, self.pc)
        self.lp = LocalProject(git_project=self.project_ogr)
        self.upstream = packit.upstream.Upstream(
            self.conf, self.pc, local_project=self.lp
        )

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.static_tmp)
