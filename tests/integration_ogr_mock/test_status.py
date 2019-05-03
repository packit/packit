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


import unittest
import os

import packit.distgit
import packit.upstream
import packit.ogr_services
from packit.config import get_package_config_from_repo
from packit.status import Status
from packit.local_project import LocalProject
from packit.config import Config

DATA_DIR = "test_data"
PERSISTENT_DATA_PREFIX = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), DATA_DIR
)


class TestStatus(unittest.TestCase):
    datafile_github = os.path.join(PERSISTENT_DATA_PREFIX, "TestStatus_github.yaml")
    datafile_pagure = os.path.join(PERSISTENT_DATA_PREFIX, "TestStatus_pagure.yaml")

    @staticmethod
    def get_test_config():
        conf = Config()
        conf._pagure_user_token = os.environ.get("PAGURE_TOKEN", "test")
        conf._pagure_fork_token = os.environ.get("PAGURE_FORK_TOKEN", "test")
        conf._github_token = os.environ.get("GITHUB_TOKEN", "test")
        return conf

    def setUp(self):
        self.conf = self.get_test_config()
        self.is_write_mode = bool(os.environ.get("FORCE_WRITE"))

        self.storage_pagure = packit.ogr_services.PersistentObjectStorage(
            self.datafile_pagure, self.is_write_mode
        )
        packit.distgit.PagureService.persistent_storage = self.storage_pagure

        self.storage_github = packit.ogr_services.PersistentObjectStorage(
            self.datafile_github, self.is_write_mode
        )
        packit.ogr_services.GithubService.persistent_storage = self.storage_github

        self.service_github = packit.ogr_services.GithubService(
            token=self.conf.github_token, persistent_storage=self.storage_github
        )
        self.project_ogr = self.service_github.get_project(
            namespace="packit-service", repo="ogr"
        )
        self.pc = get_package_config_from_repo(
            sourcegit_project=self.project_ogr, ref="master"
        )
        self.dg = packit.distgit.DistGit(self.conf, self.pc)
        self.lp = LocalProject(path_or_url=self.pc.upstream_project_url)
        self.upstream = packit.upstream.Upstream(
            self.conf, self.pc, local_project=self.lp
        )
        self.status = Status(self.conf, self.pc, self.upstream, self.dg)

    def tearDown(self):
        self.storage_pagure.dump()
        self.storage_github.dump()

    def test_status(self):
        assert self.status

    def test_distgen_versions(self):
        table = self.status.get_dg_versions()
        assert table
        assert len(table) >= 3

    def test_builds(self):
        table = self.status.get_builds()
        assert table
        assert len(table) >= 2

    def test_updates(self):
        table = self.status.get_updates()
        assert table
        assert len(table) >= 3

    def test_up_releases(self):
        table = self.status.get_up_releases()
        assert len(table) == 0

    def test_dowstream_pr(self):
        table = self.status.get_downstream_prs()
        assert len(table) == 0
