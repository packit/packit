"""
This is the python interface for packit used by ci/bots
and other tools working with multiple packages.

This API is built on top of the packit.api.
"""
import logging
from typing import Dict, Any

import requests

from packit.fed_mes_consume import Consumerino

logger = logging.getLogger(__name__)


class PackitBotApi:
    def __init__(self) -> None:
        # TODO: the url template should be configurable
        self.datagrepper_url = (
            "https://apps.fedoraproject.org/datagrepper/id?id={msg_id}&is_raw=true"
        )
        self.consumerino = Consumerino()

    def watch_upstream_pull_request(self):
        pass

    def consume_upstream_pull_request(self, fedmsg: Dict):
        pass

    def watch_fedora_ci(self):
        pass

    def consume_fedora_ci(self, fedmsg: Dict):
        pass

    def watch_upstream_release(self):
        pass

    def consume_upstream_release(self, fedmsg: Dict):
        pass

    def _fetch_fedmsg_dict(self, msg_id: str) -> Dict[str, Any]:
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
