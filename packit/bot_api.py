"""
This is the python interface for packit used by ci/bots
and other tools working with multiple packages.

This API is built on top of the packit.api.
"""
import logging
from typing import Dict, Optional

from packit.api import PackitAPI
from packit.config import Config, PackageConfig
from packit.fed_mes_consume import Consumerino
from packit.watcher import SourceGitCheckHelper

logger = logging.getLogger(__name__)


class PackitBotAPI:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.consumerino = Consumerino()

    def watch_upstream_pull_request(self):
        for topic, action, msg in self.consumerino.iterate_pull_requests():
            if action in ["opened", "synchronize", "reopened"]:
                self.sync_upstream_pull_request_with_fedmsg(fedmsg=msg)

    def sync_upstream_pull_request_with_fedmsg(self, fedmsg: Dict):
        package_config = PackageConfig.get_config_from_fedmsg(fedmsg)
        self.sync_upstream_pull_request(
            package_config=package_config, pr_id=0, dist_git_branch=""
        )

    def sync_upstream_pull_request(
        self, package_config: PackageConfig, pr_id: int, dist_git_branch: str
    ):
        logger.info("syncing the upstream code to downstream")
        packit_api = PackitAPI(config=self.config, package_config=package_config)
        packit_api.sync_pr(pr_id=pr_id, dist_git_branch=dist_git_branch)

    def watch_upstream_release(self):
        for topic, msg in self.consumerino.iterate_releases():
            self.sync_upstream_release_with_fedmsg(fedmsg=msg)

    def sync_upstream_release_with_fedmsg(self, fedmsg: Dict):
        config = PackageConfig.get_config_from_fedmsg(fedmsg)
        self.sync_upstream_release(
            package_config=config, version="", dist_git_branch=""
        )

    def sync_upstream_release(
        self,
        package_config: PackageConfig,
        version: Optional[str],
        dist_git_branch: str,
    ):
        logger.info("syncing the upstream code to downstream")
        packit_api = PackitAPI(config=self.config, package_config=package_config)
        packit_api.update(dist_git_branch=dist_git_branch)

    def watch_fedora_ci(self):
        for topic, msg in self.consumerino.iterate_dg_pr_flags():
            self.sync_fedora_ci_with_fedmsg(fedmsg=msg)

    def sync_fedora_ci_with_fedmsg(self, fedmsg: Dict):
        package_config = PackageConfig.get_config_from_fedmsg(fedmsg)
        self.sync_fedora_ci(package_config=package_config)

    def sync_fedora_ci(self, package_config: PackageConfig):
        sg = SourceGitCheckHelper(config=self.config, package_config=package_config)
        sg.process_new_dg_flag(None)
