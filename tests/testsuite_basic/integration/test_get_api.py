from packit.cli.utils import get_packit_api
from packit.local_project import LocalProject
from tests.testsuite_basic.spellbook import get_test_config


def test_is_upstream(upstream_and_remote):
    upstream, _ = upstream_and_remote
    c = get_test_config()
    api = get_packit_api(
        config=c, local_project=LocalProject(working_dir=str(upstream))
    )
    assert api.upstream_local_project
    assert not api.downstream_local_project
    assert api.upstream_local_project.working_dir == str(upstream)


def test_is_downstream(distgit_and_remote):
    downstream, _ = distgit_and_remote
    c = get_test_config()
    api = get_packit_api(
        config=c, local_project=LocalProject(working_dir=str(downstream))
    )
    assert api.downstream_local_project
    assert not api.upstream_local_project
    assert api.downstream_local_project.working_dir == str(downstream)


def test_url_is_downstream():
    c = get_test_config()
    api = get_packit_api(
        config=c,
        local_project=LocalProject(git_url="https://src.fedoraproject.org/rpms/packit"),
    )
    assert api.downstream_local_project
    assert not api.upstream_local_project


def test_url_is_upstream():
    c = get_test_config()
    api = get_packit_api(
        config=c,
        local_project=LocalProject(git_url="https://github.com/packit-service/ogr"),
    )
    assert api.upstream_local_project
    assert not api.downstream_local_project
