# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

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

from munch import Munch
from pytest import fixture

from packit.copr_helper import CoprHelper


@fixture()
def copr_build():
    # copr_client.build_proxy.get(build_id) response
    build_dict = {
        "chroots": ["fedora-29-x86_64", "fedora-30-x86_64", "fedora-rawhide-x86_64"],
        "ended_on": 1566377991,
        "id": 1010428,
        "ownername": "packit",
        "project_dirname": "packit-service-ogr-160",
        "projectname": "packit-service-ogr-160",
        "repo_url": "https://copr-be.cloud.fedoraproject.org/results/packit/packit-service-ogr-160",
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
    web_build_url = (
        "https://copr.fedorainfracloud.org/coprs/"
        "packit/packit-service-ogr-160/build/1010428/"
    )
    return Munch(build_dict), web_build_url


class TestPackitAPI:
    def test__copr_web_build_url(self, copr_build):
        assert CoprHelper.copr_web_build_url(copr_build[0]) == copr_build[1]
