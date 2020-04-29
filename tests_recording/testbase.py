import inspect
import os
import shutil
import unittest
from subprocess import check_output, CalledProcessError

from requre.helpers.tempfile import TempFile
from requre.storage import PersistentObjectStorage

import packit.distgit
import packit.upstream
from packit.config import Config, get_package_config_from_repo
from packit.exceptions import PackitException
from packit.local_project import LocalProject

DATA_DIR = "test_data"
PERSISTENT_DATA_PREFIX = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), DATA_DIR
)


class PackitUnittestOgr(unittest.TestCase):
    @staticmethod
    def get_test_config():
        try:
            conf = Config.get_user_config()
        except PackitException:
            conf = Config()
        conf.dry_run = True
        return conf

    def get_datafile_filename(self, suffix="yaml"):
        prefix = PERSISTENT_DATA_PREFIX
        test_file_name = os.path.basename(inspect.getfile(self.__class__)).rsplit(
            ".", 1
        )[0]
        test_class_name = f"{self.id()}.{suffix}"
        testdata_dirname = os.path.join(prefix, test_file_name)
        os.makedirs(testdata_dirname, mode=0o777, exist_ok=True)
        return os.path.join(testdata_dirname, test_class_name)

    def set_git_user(self):
        try:
            check_output(["git", "config", "--global", "-l"])
        except CalledProcessError:
            check_output(
                ["git", "config", "--global", "user.email", "test@example.com"]
            )
            check_output(["git", "config", "--global", "user.name", "Tester"])

    def setUp(self):
        self.conf = self.get_test_config()
        response_file = self.get_datafile_filename()
        PersistentObjectStorage().storage_file = response_file
        PersistentObjectStorage().dump_after_store = True
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
        PersistentObjectStorage().dump()
        shutil.rmtree(self.static_tmp)
