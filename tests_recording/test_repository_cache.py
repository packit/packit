# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import tempfile
import unittest
from pathlib import Path

from flexmock import flexmock

from packit.utils.repo import RepositoryCache
from requre.modules_decorate_all_methods import (
    record_tempfile_module,
    record_git_module,
)

TEST_PROJECT_URL_TO_CLONE = "https://src.fedoraproject.org/rpms/python-requre.git"
TEST_PROJECT_NAME = "python-requre"


@record_tempfile_module()
@record_git_module()
class RepositoryCacheTest(unittest.TestCase):
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

    def test_repository_cache_accept_str(self):
        tmp_path = Path(tempfile.mkdtemp())
        cache_path = tmp_path / "cache"
        clone1_path = tmp_path / "clone1"
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

        repo_cache = RepositoryCache(cache_path=str(cache_path), add_new=True)
        assert repo_cache.cached_projects == []

        assert repo_cache.get_repo(url=TEST_PROJECT_URL_TO_CLONE, directory=clone1_path)
        assert repo_cache.cached_projects == [TEST_PROJECT_NAME]
