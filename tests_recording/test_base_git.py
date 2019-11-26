import pytest

from packit.base_git import PackitRepositoryBase
from packit.config import Config, PackageConfig
from packit.exceptions import PackitException
from packit.local_project import LocalProject
from tests_recording.testbase import DistGitForTest, PackitUnittestBase


class TestBaseGit(PackitUnittestBase, DistGitForTest):
    def test_base_push_bad(self):
        b = PackitRepositoryBase(config=Config(), package_config=PackageConfig())
        b.local_project = LocalProject(
            working_dir=str(self.distgit),
            git_url="https://github.com/packit-service/ogr",
        )
        with pytest.raises(PackitException) as e:
            b.push("master")
        assert "unable to push" in str(e.value)

    def test_base_push_good(self):
        b = PackitRepositoryBase(config=Config(), package_config=PackageConfig())
        b.local_project = LocalProject(
            working_dir=str(self.distgit),
            git_url="https://github.com/packit-service/ogr",
        )
        b.local_project.git_repo.git.commit(
            allow_empty=True, message="Packit test commit"
        )
        b.push("master")
