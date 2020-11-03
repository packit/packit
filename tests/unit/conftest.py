import pytest
from flexmock import flexmock
from munch import munchify

import packit


@pytest.fixture
def bodhi_client_response():
    def response_factory(releases_list):
        releases = [
            {
                "name": name,
                "long_name": long_name,
                "id_prefix": id_prefix,
                "state": state,
            }
            for name, long_name, id_prefix, state in releases_list
        ]
        response = {"releases": releases}
        return munchify(response)

    return response_factory


@pytest.fixture()
def mock_get_aliases():
    mock_aliases_module = flexmock(packit.config.aliases)
    mock_aliases_module.should_receive("get_aliases").and_return(
        {
            "fedora-all": ["fedora-31", "fedora-32", "fedora-33", "fedora-rawhide"],
            "fedora-stable": ["fedora-31", "fedora-32"],
            "fedora-development": ["fedora-33", "fedora-rawhide"],
            "epel-all": ["epel-6", "epel-7", "epel-8"],
        }
    )
