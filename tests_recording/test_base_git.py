import pytest

from packit.exceptions import PackitException
from tests_recording.testbase import PackitUnittestBase, LocalDistGitForTest


class TestBaseGit(LocalDistGitForTest, PackitUnittestBase):
    def test_base_push_bad(self):
        with pytest.raises(PackitException) as e:
            self.repository_base.push("master")
        assert "unable to push" in str(e.value)

    def test_base_push_good(self):
        self.repository_base.local_project.git_repo.git.commit(
            allow_empty=True, message="Packit test commit"
        )
        self.repository_base.push("master")

    def test_distgit_commit_empty(self):
        with pytest.raises(PackitException) as ex:
            self.repository_base.commit("", "")
        assert (
            str(ex.value)
            == "No changes are present in the dist-git repo: nothing to commit."
        )
