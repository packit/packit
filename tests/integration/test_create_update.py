from os import chdir

import pytest
from flexmock import flexmock

from packit.api import PackitAPI
from packit.config import get_local_package_config
from tests.spellbook import get_test_config, can_a_module_be_imported


# FIXME: https://github.com/fedora-infra/bodhi/issues/3058
@pytest.mark.skipif(
    not can_a_module_be_imported("bodhi"), reason="bodhi not present, skipping"
)
@pytest.mark.parametrize(
    "branch,update_type,update_notes,koji_builds",
    (
        (
            "f30",
            "enhancement",
            "This is the best upstream release ever: {version}",
            ("foo-1-1",),
        ),
        (
            "f30",
            "enhancement",
            "This is the best upstream release ever: {version}",
            None,
        ),
    ),
)
def test_basic_bodhi_update(
    upstream_n_distgit,
    mock_remote_functionality,
    branch,
    update_type,
    update_notes,
    koji_builds,
):
    # https://github.com/fedora-infra/bodhi/issues/3058
    from bodhi.client.bindings import BodhiClient

    u, d = upstream_n_distgit
    chdir(u)
    c = get_test_config()

    pc = get_local_package_config(str(u))
    pc.upstream_project_url = str(u)
    pc.downstream_project_url = str(d)

    api = PackitAPI(c, pc)

    flexmock(
        BodhiClient,
        latest_builds=lambda package: {
            "f29-override": "sen-0.6.0-3.fc29",
            "f29-updates": "sen-0.6.0-3.fc29",
            "f29-updates-candidate": "sen-0.6.0-3.fc29",
            "f29-updates-pending": "sen-0.6.0-3.fc29",
            "f29-updates-testing": "sen-0.6.0-3.fc29",
            "f29-updates-testing-pending": "sen-0.6.0-3.fc29",
            "f30-override": "sen-0.6.0-4.fc30",
            "f30-updates": "sen-0.6.0-4.fc30",
            "f30-updates-candidate": "sen-0.6.1-1.fc30",
            "f30-updates-pending": "sen-0.6.0-4.fc30",
            "f30-updates-testing": "sen-0.6.0-4.fc30",
            "f30-updates-testing-pending": "sen-0.6.0-4.fc30",
        },
        save=lambda **kwargs: None,
    )
    api.create_update(
        dist_git_branch=branch,
        update_type=update_type,
        update_notes=update_notes,
        koji_builds=koji_builds,
    )
