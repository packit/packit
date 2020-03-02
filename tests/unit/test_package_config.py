import pytest
from flexmock import flexmock

from ogr.abstract import GitProject, GitService
from packit.config.package_config import get_specfile_path_from_repo


@pytest.mark.parametrize(
    "files,expected", [(["foo.spec"], "foo.spec"), ([], None)],
)
def test_get_specfile_path_from_repo(files, expected):
    gp = flexmock(GitProject)
    gp.should_receive("full_repo_name").and_return("a/b")
    gp.should_receive("get_files").and_return(files)
    git_project = GitProject(repo="", service=GitService(), namespace="")
    assert get_specfile_path_from_repo(project=git_project) == expected
