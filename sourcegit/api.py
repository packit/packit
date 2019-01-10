"""
This is the official python interface for source-git. This is used exclusively in the CLI.
"""

import logging
import os
from functools import lru_cache

import requests

from sourcegit.fed_mes_consume import Consumerino
from sourcegit.sync import Synchronizer
from sourcegit.watcher import SourceGitCheckHelper


logger = logging.getLogger(__name__)


class SourceGitAPI:
    def __init__(self):
        # TODO: the url template should be configurable
        self.datagrepper_url = "https://apps.fedoraproject.org/datagrepper/id?id={msg_id}&is_raw=true"
        self.consumerino = Consumerino()

    def fetch_fedmsg_dict(self, msg_id):
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

    def sync_upstream_pr_to_distgit(self, fedmsg_dict):
        """
        Take the input fedmsg (github push or pr create) and sync the content into dist-git

        :param fedmsg_dict: dict, code change on github
        :return: path to working dir
        """
        logger.info("syncing the upstream code to downstream")
        with Synchronizer(self.github_token, self.pagure_user_token, self.pagure_package_token,
                          self.pagure_fork_token) as sync:
            return sync.sync_using_fedmsg_dict(fedmsg_dict)

    def keep_syncing_upstream_pulls(self):
        """
        Watch Fedora messages and keep syncing upstream PRs downstream. This runs forever.

        :return: None
        """
        for topic, action, msg in self.consumerino.iterate_gh_pulls():
            # TODO:
            #   handle edited (what's that?)
            #   handle closed (merged & not merged)
            if action in ["opened", "synchronize", "reopened"]:
                self.sync_upstream_pr_to_distgit(msg)

    def process_ci_result(self, fedmsg_dict):
        """
        Take the CI result, figure out if it's related to source-git and if it is, report back to upstream

        :param fedmsg_dict: dict, flag added in pagure
        :return:
        """
        sg = SourceGitCheckHelper(self.github_token, self.pagure_user_token)
        sg.process_new_dg_flag(fedmsg_dict)

    def keep_fwding_ci_results(self):
        """
        Watch Fedora messages and keep reporting CI results back to upstream PRs. This runs forever.

        :return: None
        """
        for topic, msg in self.consumerino.iterate_dg_pr_flags():
            self.process_ci_result(msg)

    @property
    @lru_cache()
    def github_token(self):
        return os.environ["GITHUB_TOKEN"]

    @property
    @lru_cache()
    def pagure_user_token(self):
        return os.environ["PAGURE_USER_TOKEN"]

    @property
    @lru_cache()
    def pagure_package_token(self):
        """ this token is used to comment on pull requests """
        # FIXME: make this more easier to be used -- no need for a dedicated token
        return os.environ["PAGURE_PACKAGE_TOKEN"]

    @property
    @lru_cache()
    def pagure_fork_token(self):
        """ this is needed to create pull requests """
        # FIXME: make this more easier to be used -- no need for a dedicated token
        return os.environ["PAGURE_FORK_TOKEN"]
