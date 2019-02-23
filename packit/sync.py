from __future__ import annotations

import json
import logging

from ogr.abstract import GitService
from ogr.services.github import GithubService
from ogr.services.pagure import PagureService

from packit.config import (
    PackageConfig,
    get_packit_config_from_repo,
    get_local_package_config,
)
from packit.local_project import LocalProject
from packit.transformator import Transformator
from packit.utils import commits_to_nice_str, checkout_pr

logger = logging.getLogger(__name__)


# TODO: refactor this class, it's too complex
class Synchronizer:
    """
    One instance can be used for multiple sync actions.

    Contains api tokens.
    """

    def __init__(
            self,
            github_token: str,
            pagure_user_token: str,
            pagure_package_token: str,
            pagure_fork_token: str,
    ) -> None:
        self.github_token = github_token
        self.pagure_user_token = pagure_user_token
        self.pagure_package_token = pagure_package_token
        self.pagure_fork_token = pagure_fork_token

    @property
    def sourcegit_service(self) -> GitService:
        return GithubService(token=self.github_token)

    def get_packit_config(
            self, namespace: str, repo: str, branch: str
    ) -> PackageConfig:
        github_repo = self.sourcegit_service.get_project(repo=repo, namespace=namespace)
        return get_packit_config_from_repo(sourcegit_project=github_repo, branch=branch)

    def sync_using_fedmsg_dict(self, fedmsg_dict: dict) -> None:
        """
        Sync the pr to the dist-git.

        :param fedmsg_dict: dict, fedmsg of a newly opened PR
        """
        try:
            target_url = fedmsg_dict["msg"]["pull_request"]["base"]["repo"]["html_url"]
        except (KeyError, ValueError) as ex:
            logger.debug("ex = %s", ex)
            logger.error("invalid fedmsg format")
            return

        try:
            package_config = get_local_package_config()
            if package_config:
                logger.debug("Using local package config.")
            else:
                package_config = self.get_packit_config(
                    repo=fedmsg_dict["msg"]["pull_request"]["head"]["repo"]["name"],
                    namespace=fedmsg_dict["msg"]["pull_request"]["head"]["repo"][
                        "owner"
                    ]["login"],
                    branch=fedmsg_dict["msg"]["pull_request"]["head"]["ref"],
                )

        except Exception as ex:
            logger.info("no source-git mapping for project %s", target_url)
            return

        try:
            msg_id = fedmsg_dict["msg_id"]
        except KeyError:
            logger.error("provided message is not a fedmsg (missing msg_id)")
            return
        try:
            nice_msg = json.dumps(fedmsg_dict, indent=4)
            logger.debug(f"Processing fedmsg:\n{nice_msg}")
            self.sync(
                target_url=fedmsg_dict["msg"]["pull_request"]["base"]["repo"][
                    "html_url"
                ],
                target_ref=fedmsg_dict["msg"]["pull_request"]["base"]["ref"],
                full_name=fedmsg_dict["msg"]["pull_request"]["base"]["repo"][
                    "full_name"
                ],
                top_commit=fedmsg_dict["msg"]["pull_request"]["head"]["sha"],
                pr_id=fedmsg_dict["msg"]["pull_request"]["number"],
                pr_url=fedmsg_dict["msg"]["pull_request"]["html_url"],
                title=fedmsg_dict["msg"]["pull_request"]["title"],
                package_config=package_config,
            )
        except ConnectionError as ex:
            # TODO: Retry on connection error
            logger.warning(f"Connection error on processing a msg {msg_id}")
            logger.debug(str(ex))
            return
        except Exception as ex:
            logger.warning(f"Error on processing a msg {msg_id}")
            logger.debug(str(ex))
            return

    def sync(
            self,
            target_url: str,
            target_ref: str,
            full_name: str,
            top_commit: str,
            pr_id: int,
            pr_url: str,
            title: str,
            package_config: PackageConfig,
            repo_directory: str = None,
    ):
        """
        synchronize selected source-git pull request to respective downstream dist-git repo via a pagure pull request

        :param target_url:
        :param target_ref:
        :param full_name: str, name of the github repo (e.g. user-cont/source-git)
        :param top_commit: str, commit hash of the top commit in source-git PR
        :param pr_id:
        :param pr_url:
        :param title:
        :param package_config: PackageConfig, configuration of the sg - dg mapping
        :param repo_directory: use this directory instead of pulling the url
        :return:
        """
        logger.info("starting sync for project %s", target_url)

        sourcegit = LocalProject(
            git_url=target_url, working_dir=repo_directory, full_name=full_name
        )

        distgit = LocalProject(
            git_url=package_config.metadata["dist_git_url"],
            branch=f"source-git-{pr_id}",
            git_service=PagureService(token=self.pagure_fork_token),
            namespace="rpms",
            repo_name=package_config.metadata["package_name"],
        )

        checkout_pr(repo=sourcegit.git_repo, pr_id=pr_id)

        with Transformator(
                sourcegit=sourcegit, distgit=distgit, package_config=package_config
        ) as transformator:
            transformator.create_archive()
            transformator.copy_synced_content_to_distgit_directory(
                synced_files=package_config.synced_files
            )
            transformator.add_patches_to_specfile()

            commits = transformator.get_commits_to_upstream(upstream=target_ref)
            commits_nice_str = commits_to_nice_str(commits)

            logger.debug(f"Commits in source-git PR:\n{commits_nice_str}")

            msg = f"upstream commit: {top_commit}\n\nupstream repo: {target_url}"
            transformator.commit_distgit(title=title, msg=msg)

            project_fork = distgit.git_project.get_fork()
            if not project_fork:
                logger.info("Creating a fork.")
                distgit.git_project.fork_create()
                project_fork = distgit.git_project.get_fork()

            transformator.push_to_distgit_fork(
                project_fork=project_fork, branch_name=distgit.branch
            )

            transformator.reset_checks(
                full_name,
                pr_id,
                github_token=self.github_token,
                pagure_user_token=self.pagure_user_token,
            )
            transformator.update_or_create_dist_git_pr(
                distgit.git_project,
                pr_id,
                pr_url,
                top_commit,
                title,
                source_ref=distgit.branch,
                pagure_fork_token=self.pagure_fork_token,
                pagure_package_token=self.pagure_package_token,
            )

    def __enter__(self) -> Synchronizer:
        return self

    def __exit__(self, *args) -> None:
        pass
