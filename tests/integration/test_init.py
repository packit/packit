# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy

import yaml

from packit.utils.commands import cwd
from tests.spellbook import call_packit

PACKIT_PRECOMMIT_CONFIG = {
    "repo": "https://github.com/packit/pre-commit-hooks",
    "rev": "v1.3.0",
    "hooks": [{"id": "validate-config"}],
}


VALID_PRECOMMIT_CONFIG = {
    "repos": [
        {
            "repo": "some_url",
            "rev": "v0.0.0",
            "hooks": [{"id": "some_hook"}],
        },
    ],
}


INVALID_PRECOMMIT_CONFIG = [
    {"repos": []},
    {"other": []},
]  # type: list[dict]


def test_init_pass(upstream_without_config_not_bare):
    with cwd(upstream_without_config_not_bare):
        assert not (upstream_without_config_not_bare / ".packit.yaml").is_file()

        # This test requires packit on pythonpath
        result = call_packit(parameters=["init"])

        assert result.exit_code == 0

        assert (upstream_without_config_not_bare / ".packit.yaml").is_file()


def test_init_fail(cwd_upstream_or_distgit):
    result = call_packit(parameters=["init"], working_dir=str(cwd_upstream_or_distgit))

    assert result.exit_code == 2  # packit config already exists --force needed


def test_init_force_precommit_flag(upstream_without_precommit_config_not_bare):
    result = call_packit(
        parameters=["init", "--force-precommit"],
        working_dir=upstream_without_precommit_config_not_bare,
    )

    assert result.exit_code == 0

    config_file = upstream_without_precommit_config_not_bare / ".pre-commit-config.yaml"
    assert (config_file).is_file()

    expected = {"repos": [PACKIT_PRECOMMIT_CONFIG]}
    data = None
    with open(config_file) as f:
        data = yaml.safe_load(f)

    assert data == expected


def test_init_without_precommit_flag(upstream_without_config_not_bare):
    config_file = upstream_without_config_not_bare / ".pre-commit-config.yaml"
    user_data = {"repos": [{"repo": "some url"}]}
    with open(config_file, "w") as f:
        yaml.dump(user_data, f, default_flow_style=False)

    result = call_packit(
        parameters=["init", "--without-precommit"],
        working_dir=upstream_without_config_not_bare,
    )

    assert result.exit_code == 0

    # packit init must not modify user's file if pre-commit behaviour is skipped
    config_file = upstream_without_config_not_bare / ".pre-commit-config.yaml"
    data = None
    with open(config_file) as f:
        data = yaml.safe_load(f)

    assert data == user_data


def test_init_exclusive_flags(upstream_without_precommit_config_not_bare):
    result = call_packit(
        parameters=["init", "--without-precommit", "--force-precommit"],
        working_dir=upstream_without_precommit_config_not_bare,
    )

    assert result.exit_code == 2


def test_init_missing_precommit_config(upstream_without_precommit_config_not_bare):
    config_file = upstream_without_precommit_config_not_bare / ".pre-commit-config.yaml"
    assert not (config_file).is_file()

    result = call_packit(
        parameters=["init"],
        working_dir=upstream_without_precommit_config_not_bare,
    )

    assert result.exit_code == 0

    config_file = upstream_without_precommit_config_not_bare / ".pre-commit-config.yaml"
    assert not (config_file).is_file()


def test_init_empty_precommit_config(upstream_without_config_not_bare):
    config_file = upstream_without_config_not_bare / ".pre-commit-config.yaml"

    result = call_packit(
        parameters=["init"],
        working_dir=upstream_without_config_not_bare,
    )

    assert result.exit_code == 0

    expected = {"repos": [PACKIT_PRECOMMIT_CONFIG]}
    with open(config_file) as f:
        data = yaml.safe_load(f)

    assert data == expected


def test_init_random_precommit_config(upstream_without_config_not_bare):
    config_file = upstream_without_config_not_bare / ".pre-commit-config.yaml"
    random_data = "Random file content"
    with open(config_file, "w") as f:
        f.write(random_data)

    result = call_packit(
        parameters=["init"],
        working_dir=upstream_without_config_not_bare,
    )

    assert result.exit_code == 2

    # packit init must not modify user's file if its syntax is invalid
    with open(config_file) as f:
        data = f.read()
        assert random_data == data


def test_init_invalid_syntax_precommit_config(upstream_without_config_not_bare):
    config_file = upstream_without_config_not_bare / ".pre-commit-config.yaml"
    data = copy.deepcopy(INVALID_PRECOMMIT_CONFIG)

    with open(config_file, "w") as f:
        yaml.dump(data, f, sort_keys=False, default_flow_style=False)

    result = call_packit(
        parameters=["init"],
        working_dir=upstream_without_config_not_bare,
    )

    assert result.exit_code == 2

    # packit init must not modify user's file if its syntax is invalid
    with open(config_file) as f:
        data = yaml.safe_load(f)
    assert data == INVALID_PRECOMMIT_CONFIG


def test_init_valid_precommit_config(upstream_without_config_not_bare):
    config_file = upstream_without_config_not_bare / ".pre-commit-config.yaml"
    data = copy.deepcopy(VALID_PRECOMMIT_CONFIG)

    with open(config_file, "w") as f:
        yaml.dump(data, f, sort_keys=False, default_flow_style=False)

    result = call_packit(
        parameters=["init"],
        working_dir=upstream_without_config_not_bare,
    )

    assert result.exit_code == 0

    expected = data
    expected["repos"].append(PACKIT_PRECOMMIT_CONFIG)
    with open(config_file) as f:
        data = yaml.safe_load(f)

    assert data == expected


def test_init_preexisting_precommit_config(upstream_without_config_not_bare):
    config_file = upstream_without_config_not_bare / ".pre-commit-config.yaml"
    data = copy.deepcopy(VALID_PRECOMMIT_CONFIG)
    data["repos"].append(PACKIT_PRECOMMIT_CONFIG)

    with open(config_file, "w") as f:
        yaml.dump(data, f, sort_keys=False, default_flow_style=False)

    result = call_packit(
        parameters=["init"],
        working_dir=upstream_without_config_not_bare,
    )

    assert result.exit_code == 0

    expected = data
    with open(config_file) as f:
        data = yaml.safe_load(f)

    assert data == expected


# if user uses different revision of pre-commit hook, don't change it
def test_init_preexisting_precommit_config_different_rev(
    upstream_without_config_not_bare,
):
    config_file = upstream_without_config_not_bare / ".pre-commit-config.yaml"
    data = copy.deepcopy(VALID_PRECOMMIT_CONFIG)
    data["repos"].append(PACKIT_PRECOMMIT_CONFIG)
    data["repos"][1]["rev"] = "v1.2.1"

    with open(config_file, "w") as f:
        yaml.dump(data, f, sort_keys=False, default_flow_style=False)

    result = call_packit(
        parameters=["init"],
        working_dir=upstream_without_config_not_bare,
    )

    assert result.exit_code == 0

    expected = data
    with open(config_file) as f:
        data = yaml.safe_load(f)

    assert data == expected


def test_init_search_for_specfile_root(upstream_without_config_not_bare):
    with cwd(upstream_without_config_not_bare):
        (upstream_without_config_not_bare / "file.spec").touch()
        call_packit(parameters=["init"])

        with open(upstream_without_config_not_bare / ".packit.yaml") as f:
            assert "\nspecfile_path: file.spec\n" in f.read()


def test_init_search_for_specfile_recursive(upstream_without_config_not_bare):
    with cwd(upstream_without_config_not_bare):
        nested_path = upstream_without_config_not_bare / "awesome_directory" / "nested"
        nested_path.mkdir(parents=True, exist_ok=True)
        (nested_path / "pickle.spec").touch()
        call_packit(parameters=["init"])

        with open(upstream_without_config_not_bare / ".packit.yaml") as f:
            assert "\nspecfile_path: awesome_directory/nested/pickle.spec\n" in f.read()
