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

from subprocess import check_output
from flexmock import flexmock
from rebasehelper.exceptions import RebaseHelperError
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

from packit.api import PackitAPI
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
class ProposeUpdate(PackitTest):
    def cassette_setup(self, cassette):
        cassette.data_miner.data_type = DataTypes.Dict

    def setUp(self):
        super().setUp()
        self.set_git_user()
        self._api = None

    @property
    def api(self):
        if not self._api:
            self._api = PackitAPI(
                config=self.config,
                package_config=self.pc,
                upstream_local_project=self.lp,
            )
            self.api._up = self.upstream
            self.api._dg = self.dg
        return self._api

    def check_version_increase(self):
        """Bump version in specfile and tag it with the new version.
        Might fail if such tag already exists in requre repo.
        In that case you probably need to bump Version in fedora/python-requre.spec
        """
        filedata = self.project_specfile_location.read_text()
        # Patch the specfile with new version
        version_increase = "0.0.0"
        for line in filedata.splitlines():
            if "Version:" in line:
                version = line.rsplit(" ", 1)[1]
                v1, v2, v3 = version.split(".")
                version_increase = ".".join([v1, str(int(v2) + 1), v3])
                filedata = filedata.replace(version, version_increase)
                break
        self.project_specfile_location.write_text(filedata)
        check_output(
            f"cd {self.lp.working_dir};"
            f"git commit -m 'test change' {self._project_specfile_path.name};"
            f"git tag -a {version_increase} -m 'my version {version_increase}'",
            shell=True,
        )
        self.api.sync_release(dist_git_branch="master", force=True)

    def test_comment_in_spec(self):
        """
        change specfile little bit to have there some change, do not increase version
        """
        with self.project_specfile_location.open("a") as myfile:
            myfile.write("\n# comment\n")
        version_increase = "10.0.0"
        check_output(
            f"cd {self.lp.working_dir};"
            f"git commit -m 'test change' {self._project_specfile_path};"
            f"git tag -a {version_increase} -m 'my version {version_increase}'",
            shell=True,
        )
        self.api.sync_release(dist_git_branch="master")

    def test_changelog_sync(self):
        """
        Bump version two times and see if the changelog is synced
        when it's configured to do so.
        """
        original_upstream_spec_content = self.api.up.absolute_specfile_path.read_text()
        check_output(
            f"cd {self.lp.working_dir};"
            f"rpmdev-bumpspec {self._project_specfile_path};"
            f"rpmdev-bumpspec {self._project_specfile_path};"
            f"git commit -m 'test change' {self._project_specfile_path}",
            shell=True,
        )
        changed_upstream_spec_content = self.api.up.absolute_specfile_path.read_text()
        assert original_upstream_spec_content != changed_upstream_spec_content
        self.api.package_config.sync_changelog = True
        self.api.sync_release(dist_git_branch="master", use_local_content=True)
        new_downstream_spec_content = self.api.dg.absolute_specfile_path.read_text()
        assert changed_upstream_spec_content == new_downstream_spec_content

    def test_version_change_exception(self):
        """
        check if it raises exception, because sources are not uploaded in distgit
        Downgrade rebasehelper to version < 0.19.0
        """
        self.assertRaises(RebaseHelperError, self.check_version_increase)

    def test_version_change_mocked(self):
        """
        version is not not uploaded, so skip in this test
        """
        flexmock(self.api).should_receive("_handle_sources").and_return(None)
        self.check_version_increase()
