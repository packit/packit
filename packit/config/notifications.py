# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
from typing import Optional


class PullRequestNotificationsConfig:
    """Configuration of commenting on pull requests."""

    def __init__(self, successful_build: bool = False):
        self.successful_build = successful_build


class NotificationsConfig:
    """Configuration of notifications."""

    def __init__(
        self,
        pull_request: Optional[PullRequestNotificationsConfig] = None,
        failure_comment_message: Optional[str] = None,
    ):
        self.pull_request = pull_request or PullRequestNotificationsConfig()
        self.failure_comment_message = failure_comment_message
