# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from contextlib import suppress as does_not_raise
import pathlib

from munch import Munch
import pytest
from flexmock import flexmock

from packit.api import PackitAPI
from packit.copr_helper import CoprHelper
from packit.exceptions import PackitException
from packit.local_project import LocalProject
from packit.patches import PatchGenerator


def build_dict(copr_url, id):
    """Create a build object which uses 'copr_url' and 'id'."""
    # copr_client.build_proxy.get(build_id) response
    return Munch(
        {
            "chroots": [
                "fedora-29-x86_64",
                "fedora-30-x86_64",
                "fedora-rawhide-x86_64",
            ],
            "ended_on": 1566377991,
            "id": str(id),
            "ownername": "packit",
            "project_dirname": "packit-service-ogr-160",
            "projectname": "packit-service-ogr-160",
            "repo_url": f"{copr_url}/results/packit/packit-service-ogr-160",
            "source_package": {
                "name": "python-ogr",
                "url": "https://copr-be.cloud.fedoraproject.org/results/"
                "packit/packit-service-ogr-160/srpm-builds/01010428/"
                "python-ogr-0.6.1.dev51ge88ac83-1.fc30.src.rpm",
                "version": "0.6.1.dev51+ge88ac83-1.fc30",
            },
            "started_on": 1566377844,
            "state": "succeeded",
            "submitted_on": 1566377764,
            "submitter": "packit",
        }
    )


def copr_helper(copr_url):
    """Create a mock CoprHelper, with a copr_client configured with 'copr_url'."""
    helper = CoprHelper(flexmock())
    helper._copr_client = flexmock(config={"copr_url": copr_url})
    return helper


testdata = [
    pytest.param(
        copr_helper("https://supr.copr"),
        build_dict("https://supr.copr", 1010428),
        "https://supr.copr/coprs/build/1010428/",
        id="user",
    ),
    # The name "group" bellow is kept for historical reasons.
    # These Copr permalinks have no information in them regarding who
    # the owner of the build is (although they will have, once they redirect).
    pytest.param(
        copr_helper("https://group.copr"),
        build_dict("https://group.copr", 1010430),
        "https://group.copr/coprs/build/1010430/",
        id="group",
    ),
]


@pytest.fixture
def api_mock(config_mock, package_config_mock, upstream_mock, distgit_mock):
    api = PackitAPI(config=config_mock, package_config=package_config_mock)
    flexmock(api)
    api._up = upstream_mock
    api._dg = distgit_mock
    api.should_receive("_prepare_files_to_sync").and_return([])
    api.should_receive("_handle_sources")
    return api


@pytest.mark.parametrize(
    "helper,build,web_url",
    testdata,
)
class TestPackitAPI:
    def test_copr_web_build_url(self, helper, build, web_url):
        assert helper.copr_web_build_url(build) == web_url


@pytest.mark.parametrize(
    "version, tag, get_latest_released_return, get_specfile_version_return, expectation",
    [
        pytest.param(
            "1.1.1",
            None,
            None,
            "some.version",
            does_not_raise(),
            id="version_set(CLI_explicit)",
        ),
        pytest.param(
            None,
            "v1.1.1",
            None,
            "some.version",
            does_not_raise(),
            id="tag_set(service_mode)",
        ),
        pytest.param(
            "1.1",
            "v1.1.1",
            None,
            None,
            pytest.raises(PackitException),
            id="both_set(CLI_wrong_usage)",
        ),
        pytest.param(
            None,
            None,
            "1.1",
            "some.version",
            does_not_raise(),
            id="none_set(CLI_version_from_upstream_release_monitoring)",
        ),
        pytest.param(
            None,
            None,
            None,
            None,
            pytest.raises(PackitException),
            id="none_set(CLI_version_not_in_upstream_release_monitoring)",
        ),
    ],
)
def test_sync_release_version_tag_processing(
    version,
    tag,
    get_latest_released_return,
    get_specfile_version_return,
    expectation,
    api_mock,
):
    api_mock.up.package_config.upstream_tag_template = "v{version}"
    api_mock.up.should_receive("get_latest_released_version").and_return(
        get_latest_released_return
    )
    api_mock.up.should_receive("get_specfile_version").and_return(
        get_specfile_version_return
    )
    api_mock.should_receive("_prepare_files_to_sync").with_args(
        synced_files=[], full_version=version, upstream_tag=tag
    )
    api_mock.should_receive("push_and_create_pr").and_return(flexmock())
    flexmock(PatchGenerator).should_receive("undo_identical")
    with expectation:
        api_mock.sync_release(version=version, tag=tag, dist_git_branch="_")


def test_sync_release_do_not_create_sync_note(api_mock):
    flexmock(PatchGenerator).should_receive("undo_identical")
    flexmock(pathlib.Path).should_receive("write_text").never()
    api_mock.up.should_receive("get_specfile_version").and_return("some.version")
    api_mock.up.package_config.create_sync_note = False
    api_mock.should_receive("push_and_create_pr").and_return(flexmock())
    api_mock.sync_release(version="1.1", dist_git_branch="_")


def test_sync_release_create_sync_note(api_mock):
    flexmock(PatchGenerator).should_receive("undo_identical")
    flexmock(pathlib.Path).should_receive("write_text").once()
    api_mock.up.should_receive("get_specfile_version").and_return("some.version")
    api_mock.should_receive("push_and_create_pr").and_return(flexmock())
    api_mock.sync_release(version="1.1", dist_git_branch="_")


@pytest.mark.parametrize(
    "path, downstream_package_name, expectation",
    [
        pytest.param("/systemd", "systemd", "systemd", id="both_set"),
        pytest.param(None, "systemd", "systemd", id="both_set"),
        pytest.param("/systemd", None, "systemd", id="both_set"),
        pytest.param(None, None, None, id="none_set"),
    ],
)
def test_dg_downstream_package_name_is_set(
    api_mock, path, downstream_package_name, expectation
):
    api_mock._dg = None
    api_mock.package_config.downstream_package_name = downstream_package_name
    api_mock.downstream_local_project = LocalProject(working_dir=path)
    assert api_mock.dg.package_config.downstream_package_name == expectation
