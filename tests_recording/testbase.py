import inspect
import os
import shutil
import unittest
from pathlib import Path
from subprocess import check_output, CalledProcessError

import git
import pkg_resources

from ogr import GithubService, PagureService
from packit.api import PackitAPI
from packit.base_git import PackitRepositoryBase
from packit.config import Config, PackageConfig
from packit.config import get_package_config_from_repo
from packit.distgit import DistGit
from packit.local_project import LocalProject
from packit.upstream import Upstream
from requre.helpers.tempfile import TempFile
from requre.helpers.tempfile import TempFile as RequreTempFile
from requre.storage import DataMiner, DataTypes
from requre.storage import PersistentObjectStorage
from requre.utils import StorageMode
from tests.spellbook import initiate_git_repo, prepare_dist_git_repo, DISTGIT

DATA_DIR = "test_data"
PERSISTENT_DATA_PREFIX = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), DATA_DIR
)


class PackitUnittestBase(unittest.TestCase):
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
        super().setUp()
        response_file = self.get_datafile_filename()
        PersistentObjectStorage().storage_file = response_file
        PersistentObjectStorage().dump_after_store = True
        self.static_tmp = "/tmp/packit_tmp"
        os.makedirs(self.static_tmp, exist_ok=True)
        TempFile.root = self.static_tmp

    def tearDown(self):
        PersistentObjectStorage().dump()
        if self.static_tmp:
            shutil.rmtree(self.static_tmp)
        DataMiner().data_type = DataTypes.List
        PersistentObjectStorage().mode = StorageMode.default
        super().tearDown()


class ConfigForTest:
    @property
    def config(self):
        conf = Config()
        if PersistentObjectStorage().mode != StorageMode.read:
            conf.services = {
                GithubService(token=os.environ.get("GITHUB_TOKEN")),
                PagureService(
                    token=os.environ.get("PAGURE_TOKEN", None),
                    instance_url="https://src.fedoraproject.org",
                ),
            }
        conf.dry_run = True
        return conf


class UpstreamForTest(ConfigForTest, unittest.TestCase):
    def setUp(self):
        super().setUp()

    @property
    def upstream_project(self):
        return self.config.get_project(url="https://github.com/packit-service/ogr")

    @property
    def upstream_package_config(self):
        return get_package_config_from_repo(
            sourcegit_project=self.upstream_project, ref="master"
        )

    @property
    def upstream(self):
        return Upstream(
            self.config,
            self.upstream_package_config,
            local_project=self.upstream_local_project,
        )

    @property
    def upstream_local_project(self):
        return LocalProject(git_project=self.upstream_project)

    @property
    def upstream_packit_api(self):
        return PackitAPI(
            config=self.config,
            package_config=self.upstream_package_config,
            upstream_local_project=self.upstream_local_project,
        )


class LocalDistGitForTest(ConfigForTest, unittest.TestCase):
    def setUp(self):
        super().setUp()
        DataMiner().data_type = DataTypes.List

        self.temp_dir = Path(RequreTempFile.mkdtemp())
        self.distgit_remote = self.temp_dir / "dist_git_remote"
        self.distgit_remote.mkdir(parents=True, exist_ok=True)
        git.Repo.init(path=str(self.distgit_remote), bare=True)

        self.distgit_path = self.temp_dir / "dist_git"
        shutil.copytree(DISTGIT, self.distgit_path)
        initiate_git_repo(
            self.distgit_path,
            push=True,
            remotes=[
                ("origin", str(self.distgit_remote)),
                ("i_am_distgit", "https://src.fedoraproject.org/rpms/python-ogr"),
            ],
        )
        prepare_dist_git_repo(self.distgit_path)

    def tearDown(self):
        shutil.rmtree(self.distgit_path)
        super().tearDown()

    @property
    def repository_base(self) -> PackitRepositoryBase:
        packit_repo_base = PackitRepositoryBase(
            config=Config(), package_config=PackageConfig()
        )
        packit_repo_base.local_project = LocalProject(
            working_dir=str(self.distgit_path),
            git_url="https://github.com/packit-service/ogr",
        )
        return packit_repo_base


class DistGitForTest(ConfigForTest, unittest.TestCase):
    def setUp(self):
        super().setUp()
        DataMiner().data_type = DataTypes.List

    @property
    def distgit_project(self):
        return self.config.get_project(
            url="https://src.fedoraproject.org/rpms/python-ogr"
        )

    @property
    def distgit_package_config(self):
        return get_package_config_from_repo(
            sourcegit_project=self.distgit_project, ref="master"
        )

    @property
    def distgit_local_project(self):
        return LocalProject(git_project=self.distgit_project)

    @property
    def distgit(self):
        return DistGit(
            config=self.config,
            package_config=self.distgit_package_config,
            local_project=self.distgit_local_project,
        )


class RebaseHelperSwitch(unittest.TestCase):
    def setUp(self):
        super().setUp()
        major, minor, *_ = pkg_resources.get_distribution("rebasehelper").version.split(
            "."
        )

        if int(minor) >= 19:
            DataMiner().key += "rebase-helper>=0.19"
        else:
            DataMiner().key += "rebase-helper<0.19"


class OgrSwitch(unittest.TestCase):
    def setUp(self):
        super().setUp()
        major, minor, *_ = pkg_resources.get_distribution("ogr").version.split(".")
        DataMiner().key += f"ogr-{major}.{minor}"
