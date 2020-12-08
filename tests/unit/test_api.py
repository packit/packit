# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from contextlib import suppress as does_not_raise

from munch import Munch
import pytest
from flexmock import flexmock

from packit.api import PackitAPI
from packit.copr_helper import CoprHelper
from packit.exceptions import PackitException


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
    "version, tag, get_version_return, expectation",
    [
        pytest.param("1.1.1", None, None, does_not_raise(), id="version_set"),
        pytest.param(None, "v1.1.1", None, does_not_raise(), id="tag_set"),
        pytest.param(
            "1.1", "v1.1.1", None, pytest.raises(PackitException), id="both_set"
        ),
        pytest.param(
            None, None, "1.1", does_not_raise(), id="none_set-get_version_exists"
        ),
        pytest.param(
            None,
            None,
            None,
            pytest.raises(PackitException),
            id="none_set-get_version_None",
        ),
    ],
)
def test_sync_release_version_tag_processing(
    version, tag, get_version_return, expectation, api_mock
):
    api_mock.up.package_config.upstream_tag_template = "v{version}"
    api_mock.up.should_receive("get_version").and_return(get_version_return)
    api_mock.should_receive("_prepare_files_to_sync").with_args(
        raw_sync_files=[], full_version=version, upstream_tag=tag
    )
    with expectation:
        api_mock.sync_release(
            version=version or get_version_return, tag=tag, dist_git_branch="_"
        )
