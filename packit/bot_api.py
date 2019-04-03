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

"""
This is the python interface for packit used by ci/bots
and other tools working with multiple packages.

This API is built on top of the packit.api.
"""
import logging
from functools import lru_cache
from typing import Dict, Optional

from ogr.services.github import GithubService
from ogr.services.pagure import PagureService
from packit.local_project import LocalProject

from packit.api import PackitAPI
from packit.config import Config, PackageConfig, get_packit_config_from_repo
from packit.fed_mes_consume import Consumerino

logger = logging.getLogger(__name__)


class PackitBotAPI:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.consumerino = Consumerino()

    @property  # type: ignore
    @lru_cache()
    def _github_service(self):
        return GithubService(token=self.config.github_token)

    @property  # type: ignore
    @lru_cache()
    def _pagure_service(self):
        return PagureService(token=self.config.pagure_user_token)

    def watch_upstream_pull_request(self):
        for topic, action, msg in self.consumerino.iterate_pull_requests():
            if action in ["opened", "synchronize", "reopened"]:
                self.sync_upstream_pull_request_with_fedmsg(fedmsg=msg)

    def sync_upstream_pull_request_with_fedmsg(self, fedmsg: Dict):
        repo_name = fedmsg["msg"]["pull_request"]["head"]["repo"]["name"]
        namespace = fedmsg["msg"]["pull_request"]["head"]["repo"]["owner"]["login"]
        ref = fedmsg["msg"]["pull_request"]["head"]["ref"]
        pr_id = fedmsg["msg"]["pull_request"]["number"]

        github_repo = self._github_service.get_project(  # type: ignore
            repo=repo_name, namespace=namespace
        )
        local_project = LocalProject(git_project=github_repo)

        package_config = get_packit_config_from_repo(
            sourcegit_project=github_repo, ref=ref
        )

        if not package_config:
            logger.debug(
                f"No packit config: skipping pull-request {pr_id} for {namespace}/{repo_name}."
            )
            return
        self.sync_upstream_pull_request(
            package_config=package_config,
            pr_id=pr_id,
            dist_git_branch="master",
            upstream_local_project=local_project,
        )

    def sync_upstream_pull_request(
        self,
        package_config: PackageConfig,
        pr_id: int,
        dist_git_branch: str,
        upstream_local_project: LocalProject,
    ):
        logger.info("syncing the upstream code to downstream")
        packit_api = PackitAPI(
            config=self.config,
            package_config=package_config,
            upstream_local_project=upstream_local_project,
        )
        packit_api.sync_pr(pr_id=pr_id, dist_git_branch=dist_git_branch)

    def watch_upstream_release(self):
        """
        Listen on fedmsg and sync the upstream releases to the upstream pull-request.
        """
        for topic, msg in self.consumerino.iterate_releases():
            self.sync_upstream_release_with_fedmsg(fedmsg=msg)

    def sync_upstream_release_with_fedmsg(self, fedmsg: Dict):
        """
        Sync the upstream release to the distgit pull-request.

        :param fedmsg: fedmsg dict
        """
        repo_name = fedmsg["msg"]["repository"]["name"]
        namespace = fedmsg["msg"]["repository"]["owner"]["login"]
        version = fedmsg["msg"]["release"]["tag_name"]
        https_url = fedmsg["msg"]["repository"]["html_url"]

        github_repo = self._github_service.get_project(  # type: ignore
            repo=repo_name, namespace=namespace
        )
        local_project = LocalProject(git_project=github_repo)

        package_config = get_packit_config_from_repo(
            sourcegit_project=github_repo, ref=version
        )

        if not package_config:
            logger.info(
                f"No packit config: skipping release {version} for {namespace}/{repo_name}."
            )
            return

        if not package_config.upstream_project_url:
            package_config.upstream_project_url = https_url

        # TODO: https://github.com/packit-service/packit/issues/103
        self.sync_upstream_release(
            package_config=package_config,
            version=version,
            dist_git_branch="master",
            upstream_local_project=local_project,
        )

    def sync_upstream_release(
        self,
        package_config: PackageConfig,
        version: Optional[str],
        dist_git_branch: str,
        upstream_local_project: LocalProject,
    ):
        """
        Sync the upstream release to the distgit pull-request.

        :param package_config: PackageConfig
        :param version: not used now, str
        :param dist_git_branch: str
        :param upstream_local_project: LocalProject instance
        """
        logger.info("syncing the upstream code to downstream")
        packit_api = PackitAPI(
            config=self.config,
            package_config=package_config,
            upstream_local_project=upstream_local_project,
        )
        packit_api.sync_release(dist_git_branch=dist_git_branch, version=version)

    def watch_fedora_ci(self):
        for topic, msg in self.consumerino.iterate_dg_pr_flags():
            self.sync_fedora_ci_with_fedmsg(fedmsg=msg)

    def sync_fedora_ci_with_fedmsg(self, fedmsg: Dict):
        raise NotImplementedError(
            "The watching of the Fedora CI is not implemented yet."
        )
        """
        repo_name = fedmsg["msg"]["pull_request"]["project"]["name"]
        namespace = fedmsg["msg"]["pull_request"]["project"]["namespace"]
        pr_id = fedmsg["msg"]["pull_request"]["id"]

        pagure_repo = self._pagure_service.get_project(  # type: ignore
            repo=repo_name, namespace=namespace
        )

        pull_request = pagure_repo.get_pr_info(pr_id=pr_id)

        # TODO: Finish parsing fedmsg and call sync_fedora_ci
        """

    def sync_fedora_ci(self, package_config: PackageConfig):
        raise NotImplementedError(
            "The watching of the Fedora CI is not implemented yet."
        )
        """
        # TODO: Rework the SourceGitCheckHelper and use it

        sg = SourceGitCheckHelper(config=self.config, package_config=package_config)
        sg.process_new_dg_flag(None)
        """
