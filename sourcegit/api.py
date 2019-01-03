"""
This is the official python interface for source-git. This is used exclusively in the CLI.
"""

import logging

import requests

from sourcegit.sync import Synchronizer
from sourcegit.watcher import Holyrood

logger = logging.getLogger(__name__)


class SourceGitAPI:
    def __init__(self):
        # TODO: the url template should be configurable
        self.datagrepper_url = "https://apps.fedoraproject.org/datagrepper/id?id={msg_id}&is_raw=true"

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

    @staticmethod
    def sync_upstream_pr_to_distgit(fedmsg_dict):
        """
        Take the input fedmsg (github push or pr create) and sync the content into dist-git

        :param fedmsg_dict: dict, code change on github
        :return: path to working dir
        """
        logger.info("syncing the upstream code to downstream")
        with Synchronizer() as sync:
            return sync.sync_using_fedmsg_dict(fedmsg_dict)

    @staticmethod
    def process_ci_result(fedmsg_dict):
        """
        Take the CI result, figure out if it's related to source-git and if it is, report back to upstream

        :param fedmsg_dict: dict, flag added in pagure
        :return:
        """
        h = Holyrood()
        h.process_pr(fedmsg_dict)
