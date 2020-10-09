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


from requre.cassette import DataTypes
from requre.online_replacing import (
    apply_decorator_to_all_methods,
    record_requests_for_all_methods,
    replace_module_match,
)
from requre.helpers.tempfile import TempFile
from requre.helpers.simple_object import Simple
from requre.helpers.files import StoreFiles
from requre.helpers.git.pushinfo import PushInfoStorageList
from requre.helpers.git.fetchinfo import FetchInfoStorageList
from requre.helpers.git.repo import Repo

from packit.status import Status
from tests_recording.testbase import PackitTest


@record_requests_for_all_methods()
@apply_decorator_to_all_methods(
    replace_module_match(
        what="packit.utils.run_command_remote", decorate=Simple.decorator_plain()
    )
)
@apply_decorator_to_all_methods(
    replace_module_match(
        what="packit.fedpkg.FedPKG.clone",
        decorate=StoreFiles.where_arg_references(
            key_position_params_dict={"target_path": 2}
        ),
    )
)
@apply_decorator_to_all_methods(
    replace_module_match(
        what="git.repo.base.Repo.clone_from",
        decorate=StoreFiles.where_arg_references(
            key_position_params_dict={"to_path": 2},
            return_decorator=Repo.decorator_plain,
        ),
    )
)
@apply_decorator_to_all_methods(
    replace_module_match(
        what="git.remote.Remote.push", decorate=PushInfoStorageList.decorator_plain()
    )
)
@apply_decorator_to_all_methods(
    replace_module_match(
        what="git.remote.Remote.fetch", decorate=FetchInfoStorageList.decorator_plain()
    )
)
@apply_decorator_to_all_methods(
    replace_module_match(what="tempfile.mkdtemp", decorate=TempFile.mkdtemp())
)
@apply_decorator_to_all_methods(
    replace_module_match(what="tempfile.mktemp", decorate=TempFile.mktemp())
)
# Be aware that decorator stores login and token to test_data, replace it by some value.
# Default precommit hook doesn't do that for copr.v3.helpers, see README.md
@apply_decorator_to_all_methods(
    replace_module_match(
        what="copr.v3.helpers.config_from_file", decorate=Simple.decorator_plain()
    )
)
class TestStatus(PackitTest):
    def cassette_setup(self, cassette):
        cassette.data_miner.data_type = DataTypes.Dict

    def setUp(self):
        super().setUp()
        self._status = None

    @property
    def status(self):
        if not self._status:
            self._status = Status(self.config, self.pc, self.upstream, self.dg)
        return self._status

    def test_status(self):
        assert self.status

    def test_distgen_versions(self):
        table = self.status.get_dg_versions()
        assert table
        assert len(table) >= 3

    def test_koji_builds(self):
        table = self.status.get_koji_builds()
        assert table
        assert len(table) >= 2

    def test_copr_builds(self):
        table = self.status.get_copr_builds()
        assert table
        assert len(table) >= 2

    def test_updates(self):
        table = self.status.get_updates()
        assert table
        assert len(table) >= 3

        # Check if get_updates doesn't return more than one stable update per branch
        stable_branches = []
        for [update, _, status] in table:
            branch = update[-4:]
            if status == "stable":
                stable_branches.append(branch)
        assert len(set(stable_branches)) == len(stable_branches)

    def test_up_releases(self):
        table = self.status.get_up_releases()
        assert len(table) >= 1

    def test_dowstream_pr(self):
        table = self.status.get_downstream_prs()
        assert len(table) >= 0
