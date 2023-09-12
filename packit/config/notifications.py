# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
from typing import Optional


class PullRequestNotificationsConfig:
    """Configuration of commenting on pull requests."""

    def __init__(self, successful_build: bool = False):
        self.successful_build = successful_build


class FailureCommentNotificationsConfig:
    """Configuration of the failure comment."""

    def __init__(self, message: Optional[str] = None):
        self.message = message


class NotificationsConfig:
    """Configuration of notifications."""

    def __init__(
        self,
        pull_request: Optional[PullRequestNotificationsConfig] = None,
        failure_comment: Optional[FailureCommentNotificationsConfig] = None,
    ):
        self.pull_request = pull_request or PullRequestNotificationsConfig()
        self.failure_comment = failure_comment or FailureCommentNotificationsConfig()
