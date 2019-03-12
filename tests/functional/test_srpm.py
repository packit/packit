"""
Functional tests for srpm comand
"""

from tests.spellbook import call_real_packit


def test_srpm_command(upstream_instance):
    u, ups = upstream_instance
    call_real_packit(parameters=["--debug", "srpm"], cwd=u)
    assert list(u.glob("*.src.rpm"))[0].exists()


def test_srpm_custom_path(upstream_instance):
    u, ups = upstream_instance
    custom_path = "sooooorc.rpm"
    call_real_packit(parameters=["--debug", "srpm", "--output", custom_path], cwd=u)
    assert u.joinpath(custom_path).is_file()
