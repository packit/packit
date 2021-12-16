# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT


class PullRequestNotificationsConfig:
    """Configuration of commenting on pull requests."""

    def __init__(self, successful_build: bool = False):
        self.successful_build = successful_build


class NotificationsConfig:
    """Configuration of notifications."""

    def __init__(self, pull_request: PullRequestNotificationsConfig):
        self.pull_request = pull_request
