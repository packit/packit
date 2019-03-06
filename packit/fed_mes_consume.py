"""
The code here handles receiving messages about events and has wrappers to process them.

This module is meant to be imported in API and should be independent.
"""
import logging
from typing import Iterable, Tuple, Dict, Any

import fedmsg
import requests

from packit.constants import GH2FED_RELEASE_TOPIC

logger = logging.getLogger(__name__)


class Consumerino:
    """
    A class which provides an interface to consume messages via a callback
    """

    def __init__(self, url: str = None) -> None:
        # TODO: the url template should be configurable
        self.datagrepper_url = url or (
            "https://apps.fedoraproject.org/datagrepper/id?id={msg_id}&is_raw=true"
        )
        # timestamp = datetime.datetime.now().strftime("%Y%M%d-%H%M%S")
        # self.binding = {
        #     'exchange': 'amq.topic',  # The AMQP exchange to bind our queue to
        #     'queue': f'source-git-{timestamp}',
        #     'routing_keys': [topic],
        # }

    # def consume(self, callback):
    #     logger.info("consuming messages on queue %s, routing keys = %s",
    #                 self.binding["queue"], self.binding["routing_keys"])
    #     api.consume(callback, self.binding)

    @staticmethod
    def iterate_pull_requests() -> Iterable[Tuple[str, str, dict]]:
        """
        Provide messages for all github pull-request-related events

        Actions:
            https://developer.github.com/v3/activity/events/types/#events-api-payload-28

        :return: tuple, (full topic name, pull request action, dict with the message)
        """
        # https://github.com/fedora-infra/github2fedmsg/blob/a9c178b93aa6890e6b050e5f1c5e3297ceca463c/github2fedmsg/views/webhooks.py#L120
        topic_pre = "org.fedoraproject.prod.github.pull_request."
        for name, endpoint, topic, msg in fedmsg.tail_messages():
            # logger.debug("new message: %s", topic)
            # average load is about 5 messages a second
            if topic.startswith(topic_pre):
                logger.info("process message: %s", topic)
                action = topic.rsplit(".", 1)[1]
                yield topic, action, msg

    @staticmethod
    def _yield_messages(topic: str) -> Iterable[Tuple[str, dict]]:
        logger.info("listening on fedmsg, topic=%s", topic)
        for name, endpoint, topic, msg in fedmsg.tail_messages(topic=topic):
            yield topic, msg

    @staticmethod
    def iterate_releases() -> Iterable[Tuple[str, dict]]:
        """
        Provide messages for changes to github releases

        Actions:
            https://developer.github.com/v3/activity/events/types/#events-api-payload-28

        :return: full topic name, dict with the message
        """
        # https://github.com/fedora-infra/github2fedmsg/blob/a9c178b93aa6890e6b050e5f1c5e3297ceca463c/github2fedmsg/views/webhooks.py#L120
        return Consumerino._yield_messages(GH2FED_RELEASE_TOPIC)

    @staticmethod
    def iterate_dg_pr_flags() -> Iterable[Tuple[str, dict]]:
        """
        Provide messages when a flag is added to a pull request in dist-git

        :return: tuple, (full topic name, dict with the message)
        """
        # we can watch for runs directly:
        # "org.centos.prod.ci.pipeline.allpackages.complete"
        topic = "org.fedoraproject.prod.pagure.pull-request.flag.added"
        return Consumerino._yield_messages(topic)

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
