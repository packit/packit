import os
import shutil
from subprocess import check_output, CalledProcessError

from requre.helpers.tempfile import TempFile
from requre.base_testclass import RequreTestCase

import packit.distgit
import packit.upstream
from packit.config import Config, get_package_config_from_repo
from packit.exceptions import PackitException
from packit.local_project import LocalProject

DATA_DIR = "test_data"
PERSISTENT_DATA_PREFIX = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), DATA_DIR
)


class PackitUnittestOgr(RequreTestCase):
    @staticmethod
    def get_test_config():
        try:
            conf = Config.get_user_config()
        except PackitException:
            conf = Config()
        conf.dry_run = True
        return conf

    def set_git_user(self):
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
        os.makedirs(self.static_tmp, exist_ok=True)
        TempFile.root = self.static_tmp
        self.project_ogr = self.conf.get_project(
            url="https://github.com/packit-service/ogr"
        )

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
