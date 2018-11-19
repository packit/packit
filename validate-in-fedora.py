#!/usr/bin/python3
"""
Watch for new pull requests and changes to existing pull requests.
"""

import sys

import requests
import fedmsg
from fedmsg.consumers import FedmsgConsumer


class CupCake:
    """

    """

    def __init__(self):
        pass

    def process_pr(self, di):
        """

        :param di: dict, fedmsg of a newly opened PR
        :return:
        """
        repository = di["msg"]["repository"]["full_name"]
        top_commit = di["msg"]["pull_request"]["head"]["sha"]
        pull_request_id = di["msg"]["pull_request"]["number"]
        target_branch = di["msg"]["pull_request"]["base"]["ref"]
        print("New pull request opened: ")
        print(
            f"  Repository: {repository}\n"
            f"  Top commit: {top_commit}\n"
            f"  Pull request ID: {pull_request_id}\n"
            f"  Target branch: {target_branch}\n"
        )


# class Grinder(FedmsgConsumer):


def main():
    """
    watch for activity on github and create/update a downstream PR

    :return: int, retcode
    """
    topic = "org.fedoraproject.prod.github.pull_request.opened"

    c = CupCake()
    try:
        message_id = sys.argv[1]
    except IndexError:
        print(f"Listening on fedmsg, topic={topic}")
    else:
        if message_id in ["-h", "--help"]:
            print(f"Usage: {sys.argv[0]} [FEDMSG_UUID]")
            return 0
        # id=2018-20ba8199-b3a5-49a7-ab66-8026c82191ee
        url = f"https://apps.fedoraproject.org/datagrepper/id?id={message_id}&is_raw=true"
        response = requests.get(url)
        c.process_pr(response.json())
        return 0

    for name, endpoint, topic, msg in fedmsg.tail_messages(topic=topic):
        c.process_pr(msg)
    return 0


if __name__ == '__main__':
    sys.exit(main())
