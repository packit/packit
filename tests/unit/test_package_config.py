import pytest
from flexmock import flexmock
from packit.config import JobType, JobConfigTriggerType, JobConfig

from ogr.abstract import GitProject, GitService
from packit.config.package_config import get_specfile_path_from_repo, PackageConfig


@pytest.mark.parametrize(
    "files,expected", [(["foo.spec"], "foo.spec"), ([], None)],
)
def test_get_specfile_path_from_repo(files, expected):
    gp = flexmock(GitProject)
    gp.should_receive("full_repo_name").and_return("a/b")
    gp.should_receive("get_files").and_return(files)
    git_project = GitProject(repo="", service=GitService(), namespace="")
    assert get_specfile_path_from_repo(project=git_project) == expected


@pytest.mark.parametrize(
    "package_config, project",
    [
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.pull_request,
                        metadata={},
                    )
                ],
            ),
            None,
        ),
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.pull_request,
                        metadata={"project": "example"},
                    )
                ],
            ),
            "example",
        ),
        (
            PackageConfig(
                specfile_path="xxx",
                jobs=[
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.release,
                        metadata={"project": "example1"},
                    ),
                    JobConfig(
                        type=JobType.copr_build,
                        trigger=JobConfigTriggerType.pull_request,
                        metadata={"project": "example2"},
                    ),
                ],
            ),
            "example1",
        ),
    ],
)
def test_project_from_copr_build_job(package_config, project):
    config_project_value = package_config.get_copr_build_project_value()
    assert config_project_value == project
