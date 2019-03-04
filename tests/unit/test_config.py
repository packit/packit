import pytest
from jsonschema.exceptions import ValidationError

from packit.config import JobConfig, PackageConfig, TriggerType


def test_job_config_equal():
    assert JobConfig(
        trigger=TriggerType.release, release_to=["f28"], metadata={}
    ) == JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})


def test_job_config_not_equal():
    assert not JobConfig(
        trigger=TriggerType.release, release_to=["f28"], metadata={}
    ) == JobConfig(trigger=TriggerType.release, release_to=["f29"], metadata={})


@pytest.mark.parametrize(
    "raw,is_valid",
    [
        ({}, False),
        ({"trigger": "release"}, False),
        ({"release_to": ["f28"]}, False),
        ({"trigger": "release", "release_to": ["f28"]}, True),
        ({"trigger": "pull_request", "release_to": ["f28"]}, True),
        ({"trigger": "git_tag", "release_to": ["f28"]}, True),
        ({"trigger": "release", "release_to": ["f28", "rawhide", "f29"]}, True),
        (
                {
                    "trigger": "release",
                    "release_to": ["f28"],
                    "some": "other",
                    "metadata": "info",
                },
                True,
        ),
    ],
)
def test_job_config_validate(raw, is_valid):
    assert JobConfig.is_dict_valid(raw) == is_valid


@pytest.mark.parametrize("raw", [{}, {"trigger": "release"}, {"release_to": ["f28"]}])
def test_job_config_parse_error(raw):
    with pytest.raises(Exception):
        JobConfig.get_from_dict(raw_dict=raw)


@pytest.mark.parametrize(
    "raw,expected_config",
    [
        (
                {"trigger": "release", "release_to": ["f28"]},
                JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={}),
        ),
        (
                {"trigger": "pull_request", "release_to": ["f28"]},
                JobConfig(
                    trigger=TriggerType.pull_request, release_to=["f28"], metadata={}
                ),
        ),
        (
                {"trigger": "git_tag", "release_to": ["f28"]},
                JobConfig(trigger=TriggerType.git_tag, release_to=["f28"], metadata={}),
        ),
        (
                {"trigger": "release", "release_to": ["f28", "rawhide", "f29"]},
                JobConfig(
                    trigger=TriggerType.release,
                    release_to=["f28", "rawhide", "f29"],
                    metadata={},
                ),
        ),
        (
                {
                    "trigger": "release",
                    "release_to": ["f28"],
                    "some": "other",
                    "metadata": "info",
                },
                JobConfig(
                    trigger=TriggerType.release,
                    release_to=["f28"],
                    metadata={"some": "other", "metadata": "info"},
                ),
        ),
    ],
)
def test_job_config_parse(raw, expected_config):
    job_config = JobConfig.get_from_dict(raw_dict=raw)
    assert job_config == expected_config


def test_package_config_equal():
    assert PackageConfig(
        specfile_path="fedora/package.spec",
        synced_files=["a", "b"],
        jobs=[JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})],
        metadata={"c": "d"},
    ) == PackageConfig(
        specfile_path="fedora/package.spec",
        synced_files=["a", "b"],
        jobs=[JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})],
        metadata={"c": "d"},
    )


@pytest.mark.parametrize(
    "not_equal_package_config",
    [
        PackageConfig(
            specfile_path="fedora/other-package.spec",
            synced_files=["a", "b"],
            jobs=[
                JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})
            ],
            metadata={"c": "d"},
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=["b"],
            jobs=[
                JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})
            ],
            metadata={"c": "d"},
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=["a", "b"],
            jobs=[
                JobConfig(
                    trigger=TriggerType.pull_request, release_to=["f28"], metadata={}
                )
            ],
            metadata={"c": "d"},
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=["a", "b"],
            jobs=[
                JobConfig(trigger=TriggerType.release, release_to=["f29"], metadata={})
            ],
            metadata={"c": "d"},
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=["a", "b"],
            jobs=[
                JobConfig(
                    trigger=TriggerType.release, release_to=["f28"], metadata={"a": "b"}
                )
            ],
            metadata={"c": "d"},
        ),
        PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=["a", "b"],
            jobs=[
                JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})
            ],
            metadata={"c": "dddd"},
        ),
    ],
)
def test_package_config_not_equal(not_equal_package_config):
    assert (
        not PackageConfig(
            specfile_path="fedora/package.spec",
            synced_files=["a", "b"],
            jobs=[
                JobConfig(trigger=TriggerType.release, release_to=["f28"], metadata={})
            ],
            metadata={"c": "d"},
        )
        == not_equal_package_config
    )


@pytest.mark.parametrize(
    "raw,is_valid",
    [
        ({}, False),
        ({"specfile_path": "fedora/package.spec"}, False),
        ({"synced_files": ["fedora/package.spec"]}, False),
        ({"jobs": [{"trigger": "release", "release_to": ["f28"]}]}, False),
        (
                {
                    "specfile_path": "fedora/package.spec",
                    "synced_files": ["fedora/package.spec"],
                    "jobs": [{"trigger": "release", "release_to": ["f28"]}],
                },
                True,
        ),
        (
                {
                    "specfile_path": "fedora/package.spec",
                    "synced_files": ["fedora/package.spec", "other", "directory"],
                    "jobs": [
                        {"trigger": "release", "release_to": ["f28"]},
                        {"trigger": "pull_request", "release_to": ["f29", "f30", "master"]},
                    ],
                },
                True,
        ),
        (
                {
                    "specfile_path": "fedora/package.spec",
                    "synced_files": [],
                    "jobs": [
                        {"trigger": "release", "release_to": ["f28"]},
                        {"trigger": "pull_request", "release_to": ["f29", "f30", "master"]},
                        {"trigger": "git_tag", "release_to": ["f29", "f30", "master"]},
                    ],
                },
                True,
        ),
    ],
)
def test_package_config_validate(raw, is_valid):
    if not is_valid:
        with pytest.raises(ValidationError):
            PackageConfig.validate_dict(raw)
    else:
        PackageConfig.validate_dict(raw)


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"something": "different"},
        {"synced_files": ["fedora/package.spec"]},
        {"jobs": [{"trigger": "release", "release_to": ["f28"]}]},
    ],
)
def test_package_config_parse_error(raw):
    with pytest.raises(Exception):
        PackageConfig.get_from_dict(raw_dict=raw)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
                {
                    "specfile_path": "fedora/package.spec",
                    "synced_files": ["fedora/package.spec"],
                    "jobs": [{"trigger": "release", "release_to": ["f28"]}],
                },
                PackageConfig(
                    specfile_path="fedora/package.spec",
                    synced_files=["fedora/package.spec"],
                    jobs=[
                        JobConfig(
                            trigger=TriggerType.release, release_to=["f28"], metadata={}
                        )
                    ],
                    metadata={},
                ),
        ),
        (
                {
                    "specfile_path": "fedora/package.spec",
                    "synced_files": [
                        "fedora/package.spec",
                        "some",
                        "other",
                        "directory/files",
                    ],
                    "jobs": [{"trigger": "release", "release_to": ["f28"]}],
                },
                PackageConfig(
                    specfile_path="fedora/package.spec",
                    synced_files=[
                        "fedora/package.spec",
                        "some",
                        "other",
                        "directory/files",
                    ],
                    jobs=[
                        JobConfig(
                            trigger=TriggerType.release, release_to=["f28"], metadata={}
                        )
                    ],
                    metadata={},
                ),
        ),
        (
                {
                    "specfile_path": "fedora/package.spec",
                    "synced_files": [
                        "fedora/package.spec",
                        "some",
                        "other",
                        "directory/files",
                    ],
                    "jobs": [{"trigger": "release", "release_to": ["f28"]}],
                },
                PackageConfig(
                    specfile_path="fedora/package.spec",
                    synced_files=[
                        "fedora/package.spec",
                        "some",
                        "other",
                        "directory/files",
                    ],
                    jobs=[
                        JobConfig(
                            trigger=TriggerType.release, release_to=["f28"], metadata={}
                        )
                    ],
                    metadata={},
                ),
        ),
        (
                {
                    "specfile_path": "fedora/package.spec",
                    "synced_files": [
                        "fedora/package.spec",
                        "some",
                        "other",
                        "directory/files",
                    ],
                    "jobs": [{"trigger": "release", "release_to": ["f28"]}],
                    "something": "stupid",
                },
                PackageConfig(
                    specfile_path="fedora/package.spec",
                    synced_files=[
                        "fedora/package.spec",
                        "some",
                        "other",
                        "directory/files",
                    ],
                    jobs=[
                        JobConfig(
                            trigger=TriggerType.release, release_to=["f28"], metadata={}
                        )
                    ],
                    metadata={"something": "stupid"},
                ),
        ),
        (
                {
                    "specfile_path": "fedora/package.spec",
                    "synced_files": [
                        "fedora/package.spec",
                        "some",
                        "other",
                        "directory/files",
                    ],
                    "jobs": [{"trigger": "release", "release_to": ["f28"]}],
                    "something": "stupid",
                },
                PackageConfig(
                    specfile_path="fedora/package.spec",
                    synced_files=[
                        "fedora/package.spec",
                        "some",
                        "other",
                        "directory/files",
                    ],
                    jobs=[
                        JobConfig(
                            trigger=TriggerType.release, release_to=["f28"], metadata={}
                        )
                    ],
                    metadata={"something": "stupid"},
                ),
        ),
    ],
)
def test_package_config_parse(raw, expected):
    package_config = PackageConfig.get_from_dict(raw_dict=raw)
    assert package_config
    assert package_config == expected
