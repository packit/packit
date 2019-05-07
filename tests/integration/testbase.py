import unittest
import os
import inspect
from subprocess import check_output, CalledProcessError

import packit.distgit
import packit.upstream
import packit.ogr_services
from packit.config import get_package_config_from_repo
from packit.local_project import LocalProject
from packit.config import Config
from ogr.mock_core import PersistentObjectStorage


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

    def get_datafile_filename(self, service_name, suffix="yaml"):
        prefix = PERSISTENT_DATA_PREFIX
        test_file_name = os.path.basename(inspect.getfile(self.__class__)).rsplit(
            ".", 1
        )[0]
        test_class_name = f"{self.id()}_{service_name}.{suffix}"
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
        file_pagure = self.get_datafile_filename(service_name="pagure")
        file_github = self.get_datafile_filename(service_name="github")
        self.is_write_mode = bool(os.environ.get("FORCE_WRITE"))
        self.storage_pagure = PersistentObjectStorage(file_pagure, self.is_write_mode)
        self.storage_github = PersistentObjectStorage(file_github, self.is_write_mode)
        # put peristent storage class attribute to pagure and github where it is used
        packit.distgit.PagureService.persistent_storage = self.storage_pagure
        packit.ogr_services.GithubService.persistent_storage = self.storage_github

        self.service_github = packit.ogr_services.GithubService(
            token=self.conf.github_token
        )
        self.project_ogr = self.service_github.get_project(
            namespace="packit-service", repo="ogr"
        )
        self.pc = get_package_config_from_repo(
            sourcegit_project=self.project_ogr, ref="master"
        )
        self.dg = packit.distgit.DistGit(self.conf, self.pc)
        self.lp = LocalProject(git_project=self.project_ogr)
        self.upstream = packit.upstream.Upstream(
            self.conf, self.pc, local_project=self.lp
        )

    def tearDown(self):
        self.storage_pagure.dump()
        self.storage_github.dump()
