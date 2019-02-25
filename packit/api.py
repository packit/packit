"""
This is the official python interface for source-git. This is used exclusively in the CLI.
"""

import logging
from typing import Any, Dict

import requests

from packit.distgit import DistGit
from packit.fed_mes_consume import Consumerino
from packit.sync import Synchronizer
from packit.upstream import Upstream
from packit.watcher import SourceGitCheckHelper

logger = logging.getLogger(__name__)


class PackitAPI:
    def __init__(self, config):
        # TODO: the url template should be configurable
        self.datagrepper_url = (
            "https://apps.fedoraproject.org/datagrepper/id?id={msg_id}&is_raw=true"
        )
        self.consumerino = Consumerino()
        self.config = config

    def fetch_fedmsg_dict(self, msg_id: str) -> Dict[str, Any]:
        """
        Fetch selected message from datagrepper

        :param msg_id: str
        :return: dict, the fedmsg
        """
        logger.debug(f"Proccessing message: {msg_id}")
        url = self.datagrepper_url.format(msg_id=msg_id)
        response = requests.get(url)
        msg_dict = response.json()
        return msg_dict

    def sync_upstream_pr_to_distgit(self, fedmsg_dict: Dict[str, Any]) -> None:
        """
        Take the input fedmsg (github push or pr create) and sync the content into dist-git

        :param fedmsg_dict: dict, code change on github
        """
        logger.info("syncing the upstream code to downstream")
        with Synchronizer(self.config) as sync:
            sync.sync_using_fedmsg_dict(fedmsg_dict)

    def keep_syncing_upstream_pulls(self) -> None:
        """
        Watch Fedora messages and keep syncing upstream PRs downstream. This runs forever.
        """
        with Synchronizer(self.config) as sync:
            for topic, action, msg in self.consumerino.iterate_gh_pulls():
                # TODO:
                #   handle edited (what's that?)
                #   handle closed (merged & not merged)
                if action in ["opened", "synchronize", "reopened"]:
                    sync.sync_using_fedmsg_dict(msg)

    def process_ci_result(self, fedmsg_dict: Dict[str, Any]) -> None:
        """
        Take the CI result, figure out if it's related to source-git and if it is, report back to upstream

        :param fedmsg_dict: dict, flag added in pagure
        """
        sg = SourceGitCheckHelper(self.config)
        sg.process_new_dg_flag(fedmsg_dict)

    def keep_fwding_ci_results(self) -> None:
        """
        Watch Fedora messages and keep reporting CI results back to upstream PRs. This runs forever.
        """
        for topic, msg in self.consumerino.iterate_dg_pr_flags():
            self.process_ci_result(msg)

    def update(self, dist_git_branch: str):
        """
        Update given package in Fedora
        """
        dg = DistGit(self.config)
        up = Upstream(self.config)
        full_version = up.specfile.get_full_version()
        local_pr_branch = f"{full_version}-update"
        # fetch and reset --hard upstream/$branch?
        dg.checkout_branch(dist_git_branch)
        dg.create_branch(local_pr_branch)
        dg.checkout_branch(local_pr_branch)

        dg.sync_files(up.lp)
        archive = dg.download_upstream_archive()

        dg.upload_to_lookaside_cache(archive)

        dg.commit(f"{full_version} upstream release", "more info")
        dg.create_pull(
            f"Update to upstream release {full_version}",
            "description",
            local_pr_branch,
            dist_git_branch
        )
