# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import shutil
import tempfile
import unittest
from os import makedirs
from pathlib import Path

from flexmock import flexmock

from packit.utils.repo import RepositoryCache
from requre.helpers.files import StoreFiles
from requre.helpers.git.repo import Repo
from requre.helpers.tempfile import TempFile
from requre.online_replacing import apply_decorator_to_all_methods, replace

TEST_PROJECT_URL_TO_CLONE = "https://src.fedoraproject.org/rpms/python-requre.git"
TEST_PROJECT_NAME = "python-requre"


@apply_decorator_to_all_methods(
    replace(what="tempfile.mkdtemp", decorate=TempFile.mkdtemp())
)
@apply_decorator_to_all_methods(
    replace(
        what="git.repo.base.Repo.clone_from",
        decorate=StoreFiles.where_arg_references(
            key_position_params_dict={"to_path": 2},
            return_decorator=Repo.decorator_plain,
        ),
    )
)
class RepositoryCacheTest(unittest.TestCase):
    def setUp(self):
        self.static_tmp = "/tmp/packit_tmp_repository_cache"
        makedirs(self.static_tmp, exist_ok=True)
        TempFile.root = self.static_tmp

    def tearDown(self):
        shutil.rmtree(self.static_tmp)

    def test_repository_cache_add_new_and_use_it(self):
        tmp_path = Path(tempfile.mkdtemp())
        cache_path = tmp_path / "cache"
        clone1_path = tmp_path / "clone1"
        clone2_path = tmp_path / "clone2"
        flexmock(RepositoryCache).should_call("_clone").with_args(
            url=TEST_PROJECT_URL_TO_CLONE,
            to_path=str(cache_path / TEST_PROJECT_NAME),
            tags=True,
        )
        flexmock(RepositoryCache).should_call("_clone").with_args(
            url=TEST_PROJECT_URL_TO_CLONE,
            to_path=str(clone1_path),
            reference=str(cache_path / TEST_PROJECT_NAME),
            tags=True,
        )
        flexmock(RepositoryCache).should_call("_clone").with_args(
            url=TEST_PROJECT_URL_TO_CLONE,
            to_path=str(clone2_path),
            reference=str(cache_path / TEST_PROJECT_NAME),
            tags=True,
        )

        repo_cache = RepositoryCache(cache_path=cache_path, add_new=True)
        assert repo_cache.cached_projects == []

        assert repo_cache.get_repo(url=TEST_PROJECT_URL_TO_CLONE, directory=clone1_path)
        assert repo_cache.cached_projects == [TEST_PROJECT_NAME]

        assert repo_cache.get_repo(url=TEST_PROJECT_URL_TO_CLONE, directory=clone2_path)
        assert repo_cache.cached_projects == [TEST_PROJECT_NAME]

    def test_repository_cache_do_not_add_new_if_not_enabled(self):
        tmp_path = Path(tempfile.mkdtemp())
        cache_path = tmp_path / "cache"
        clone_path = tmp_path / "clone1"
        flexmock(RepositoryCache).should_call("_clone").with_args(
            url=TEST_PROJECT_URL_TO_CLONE, to_path=str(clone_path), tags=True
        )

        repo_cache = RepositoryCache(cache_path=cache_path, add_new=False)
        assert repo_cache.cached_projects == []

        assert repo_cache.get_repo(url=TEST_PROJECT_URL_TO_CLONE, directory=clone_path)
        assert repo_cache.cached_projects == []
