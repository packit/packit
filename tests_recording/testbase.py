# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import os
import shutil
from subprocess import check_output, CalledProcessError
import unittest
from pathlib import Path
import tempfile
import packit.distgit
import packit.upstream
from packit.config import Config, get_package_config_from_repo
from packit.exceptions import PackitException
from packit.local_project import LocalProject


def socket_guard(*args, **kwargs):
    raise Exception("Internet connection not allowed")


class PackitTest(unittest.TestCase):
    def setUp(self):
        self._static_tmp = None
        self._config = None
        self._project = None
        # if you can, use this project to perform testing
        self._project_url = "https://github.com/packit/requre"
        self._project_specfile_path = Path("fedora", "python-requre.spec")
        self._pc = None
        self._dg = None
        self._lp = None
        self._upstream = None

    def tearDown(self):
        if self._static_tmp and os.path.exists(self._static_tmp):
            shutil.rmtree(self.static_tmp, ignore_errors=True)
            self._static_tmp = None

    @property
    def static_tmp(self):
        if not self._static_tmp:
            self._static_tmp = tempfile.mkdtemp()
            os.makedirs(self._static_tmp, exist_ok=True)
        return self._static_tmp

    @property
    def config(self):
        if not self._config:
            try:
                self._config = Config.get_user_config()
            except PackitException:
                self._config = Config()
        return self._config

    @property
    def project(self):
        if not self._project:
            self._project = self.config.get_project(url=self._project_url)
        return self._project

    @property
    def pc(self):
        if not self._pc:
            self._pc = get_package_config_from_repo(project=self.project)
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
    def configure_git():
        try:
            check_output(["git", "config", "--global", "-l"])
        except CalledProcessError:
            check_output(
                ["git", "config", "--global", "user.email", "test@example.com"]
            )
            check_output(["git", "config", "--global", "user.name", "Tester"])
            check_output(["git", "config", "--global", "safe.directory", "*"])
