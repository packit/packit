import yaml

from tests.testsuite_basic.spellbook import call_real_packit_and_return_exit_code


def test_generate_pass(upstream_without_config):
    packit_yaml_path = upstream_without_config / ".packit.yaml"
    assert not packit_yaml_path.is_file()

    # This test requires packit on pythonpath
    result = call_real_packit_and_return_exit_code(
        parameters=["generate"], cwd=str(upstream_without_config)
    )
    assert result == 0

    assert packit_yaml_path.is_file()
    yaml.safe_load(packit_yaml_path.read_text())


def test_generate_fail(cwd_upstream_or_distgit):
    result = call_real_packit_and_return_exit_code(
        parameters=["generate"], cwd=str(cwd_upstream_or_distgit)
    )

    assert result == 2  # packit config already exists --force needed
