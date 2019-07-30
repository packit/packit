import inspect
import os
import unittest
from subprocess import check_output, CalledProcessError

import packit.distgit
import packit.upstream

try:
    # ogr < 0.5
    from ogr import GithubService
except ImportError:
    # ogr >= 0.5
    from ogr.services.github import GithubService
try:
    # ogr < 0.5
    from ogr.mock_core import PersistentObjectStorage
except ImportError:
    # ogr >= 0.5
    from ogr.persistent_storage import PersistentObjectStorage
from packit.config import Config
from packit.config import get_package_config_from_repo
from packit.local_project import LocalProject

DATA_DIR = "test_data"
PERSISTENT_DATA_PREFIX = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), DATA_DIR
)


class PackitUnittestOgr(unittest.TestCase):
    @staticmethod
    def get_test_config():
        conf = Config()
        conf._pagure_user_token = os.environ.get("PAGURE_TOKEN", "test")
        conf._pagure_fork_token = os.environ.get("PAGURE_FORK_TOKEN", "test")
        conf._github_token = os.environ.get("GITHUB_TOKEN", "test")
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

        self.service_github = GithubService(token=self.conf.github_token)
        self.project_ogr = self.service_github.get_project(
            namespace="packit-service", repo="ogr"
        )
        self.pc = get_package_config_from_repo(
            sourcegit_project=self.project_ogr, ref="master"
        )
        if not self.pc:
            raise RuntimeError("Package config not found.")
        self.dg = packit.distgit.DistGit(self.conf, self.pc)
        self.lp = LocalProject(git_project=self.project_ogr)
        self.upstream = packit.upstream.Upstream(
            self.conf, self.pc, local_project=self.lp
        )

    def tearDown(self):
        PersistentObjectStorage().dump()
