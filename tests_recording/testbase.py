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
import unittest
from requre.helpers.tempfile import TempFile
from pathlib import Path

import packit.distgit
import packit.upstream
from packit.config import Config, get_package_config_from_repo
from packit.exceptions import PackitException
from packit.local_project import LocalProject


def socket_guard(*args, **kwargs):
    raise Exception("Internet connection not allowed")


class PackitTest(unittest.TestCase):
    def setUp(self):
        self.static_tmp = "/tmp/packit_tmp"
        makedirs(self.static_tmp, exist_ok=True)
        TempFile.root = self.static_tmp

        self._config = None
        self._project = None
        self._project_url = "https://github.com/packit/requre"
        self._project_specfile_path = Path("fedora", "python-requre.spec")
        self._pc = None
        self._dg = None
        self._lp = None
        self._upstream = None

    def tearDown(self):
        shutil.rmtree(self.static_tmp)

    @property
    def config(self):
        if not self._config:
            try:
                self._config = Config.get_user_config()
            except PackitException:
                self._config = Config()
            self._config.dry_run = True
        return self._config

    @property
    def project(self):
        if not self._project:
            self._project = self.config.get_project(url=self._project_url)
        return self._project

    @property
    def pc(self):
        if not self._pc:
            self._pc = get_package_config_from_repo(project=self.project, ref="master")
            if not self._pc:
                raise RuntimeError("Package config not found.")
        return self._pc

    @property
    def dg(self):
        if not self._dg:
            self._dg = packit.distgit.DistGit(self.config, self.pc)
        return self._dg

    @property
    def lp(self):
        if not self._lp:
            self._lp = LocalProject(git_project=self.project)
        return self._lp

    @property
    def upstream(self):
        if not self._upstream:
            self._upstream = packit.upstream.Upstream(
                self.config, self.pc, local_project=self.lp
            )
        return self._upstream

    @property
    def project_specfile_location(self):
        return self.lp.working_dir / self._project_specfile_path

    @staticmethod
    def set_git_user():
        try:
            check_output(["git", "config", "--global", "-l"])
        except CalledProcessError:
            check_output(
                ["git", "config", "--global", "user.email", "test@example.com"]
            )
            check_output(["git", "config", "--global", "user.name", "Tester"])
