from packit.utils import cwd

from tests.spellbook import call_packit


def test_generate_pass(upstream_without_config):
    with cwd(upstream_without_config):
        assert not (upstream_without_config / ".packit.yaml").is_file()

        # This test requires packit on pythonpath
        result = call_packit(parameters=["generate"])

        assert result.exit_code == 0

        assert (upstream_without_config / ".packit.yaml").is_file()


def test_generate_fail(cwd_upstream_or_distgit):
    result = call_packit(
        parameters=["generate"], working_dir=str(cwd_upstream_or_distgit)
    )

    assert result.exit_code == 2  # packit config already exists --force needed
