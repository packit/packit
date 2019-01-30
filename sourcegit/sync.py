import json
import logging
import os
import shutil
import tempfile
from functools import lru_cache
from typing import List

import git

from ogr.services.pagure import PagureService
from sourcegit.constants import DG_PR_COMMENT_KEY_SG_PR, DG_PR_COMMENT_KEY_SG_COMMIT
from sourcegit.downstream_checks import get_check_by_name
from sourcegit.transformator import Transformator, get_package_mapping
from sourcegit.utils import commits_to_nice_str
from sourcegit.watcher import SourceGitCheckHelper

logger = logging.getLogger(__name__)


class Synchronizer:
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

        # FIXME: there is an easy race condition here: if two threads use the same instance and
        #        one starts cleaning, the other gets borked; rework this so there is no such attribute
        #        on the class
        self._tempdirs: List[str] = []

    def reset_checks(self, full_name: str, pr_id: int, checks_list: list) -> None:
        """
        Before syncing a new change downstream, we need to reset status of checks for all the configured tests
        and wait for testing systems to get us the new ones.

        :param full_name: name of the repo: namespace/repo
        :param pr_id: ID of the pr
        :param checks_list: list of checks to set
        :return:
        """
        sg = SourceGitCheckHelper(self.github_token, self.pagure_user_token)
        for check_dict in checks_list:
            check = get_check_by_name(check_dict["name"])
            sg.set_init_check(full_name, pr_id, check)

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
            package_config = get_package_mapping()[target_url]
        except KeyError:
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
                source_ref=fedmsg_dict["msg"]["pull_request"]["head"]["ref"],
                full_name=fedmsg_dict["msg"]["pull_request"]["base"]["repo"][
                    "full_name"
                ],
                top_commit=fedmsg_dict["msg"]["pull_request"]["head"]["sha"],
                pr_id=fedmsg_dict["msg"]["pull_request"]["number"],
                pr_url=fedmsg_dict["msg"]["pull_request"]["html_url"],
                title=fedmsg_dict["msg"]["pull_request"]["title"],
                package_config=package_config,
            )
        except Exception as ex:
            logger.warning(f"Error on processing a msg {msg_id}")
            logger.debug(str(ex))
            return

    def sync(
            self,
            target_url,
            target_ref,
            source_ref,
            full_name,
            top_commit,
            pr_id,
            pr_url,
            title,
            package_config,
    ):
        """
        synchronize selected source-git pull request to respective downstream dist-git repo via a pagure pull request

        :param target_url:
        :param target_ref:
        :param source_ref:
        :param full_name: str, name of the github repo (e.g. user-cont/source-git)
        :param top_commit: str, commit hash of the top commit in source-git PR
        :param pr_id:
        :param pr_url:
        :param title:
        :param package_config: dict, configuration of the sg - dg mapping
        :return:
        """
        logger.info("starting sync for project %s", target_url)
        repo = self.get_repo(url=target_url)
        self.checkout_pr(repo=repo, pr_id=pr_id)

        with Transformator(
                url=target_url,
                repo=repo,
                branch=repo.active_branch,
                upstream_name=package_config["upstream_name"],
                package_name=package_config["package_name"],
                dist_git_url=package_config["dist_git_url"],
        ) as transformator:
            transformator.clone_dist_git_repo()

            dist_git_branch_name = f"source-git-{pr_id}"
            dist_git_new_branch = transformator.dist_git_repo.create_head(
                dist_git_branch_name
            )
            dist_git_new_branch.checkout()

            transformator.create_archive()
            transformator.copy_redhat_content_to_dest_dir()
            patches = transformator.create_patches()
            transformator.add_patches_to_specfile(patch_list=patches)
            transformator.repo.index.write()

            commits = transformator.get_commits_to_upstream(upstream=target_ref)
            commits_nice_str = commits_to_nice_str(commits)

            logger.debug(f"Commits in source-git PR:\n{commits_nice_str}")

            msg = f"upstream commit: {top_commit}\n\nupstream repo: {target_url}"
            transformator.commit_distgit(title=title, msg=msg)

            package_name = package_config["package_name"]
            pagure = PagureService(token=self.pagure_user_token)

            project = pagure.get_project(repo=package_name, namespace="rpms")

            project_fork = project.get_fork()
            if not project_fork:
                logger.info("Creating a fork.")
                project.fork_create()
                project_fork = project.get_fork()

            transformator.dist_git_repo.create_remote(
                name="origin-fork", url=project_fork.get_git_urls()["ssh"]
            )
            # I suggest to comment this one while testing when the push is not needed
            transformator.dist_git_repo.remote("origin-fork").push(
                refspec=dist_git_branch_name,
                force=dist_git_branch_name in project_fork.get_branches(),
            )

            self.reset_checks(full_name, pr_id, package_config["checks"])
            self._update_or_create_dist_git_pr(
                project,
                pr_id,
                pr_url,
                top_commit,
                title,
                source_ref=dist_git_branch_name,
            )

    @lru_cache()
    def get_repo(self, url, directory=None):
        if not directory:
            tempdir = tempfile.mkdtemp()
            self._tempdirs.append(tempdir)
            directory = tempdir

        # TODO: optimize cloning: single branch and last n commits?
        if os.path.isdir(os.path.join(directory, ".git")):
            logger.debug("Source git repo exists.")
            repo = git.repo.Repo(directory)
        else:
            logger.info(f"Cloning source-git repo: {url} -> {directory}")
            repo = git.repo.Repo.clone_from(url=url, to_path=directory, tags=True)

        return repo

    def checkout_pr(self, repo, pr_id):
        repo.remote().fetch(refspec=f"pull/{pr_id}/head:pull/{pr_id}")
        repo.refs[f"pull/{pr_id}"].checkout()

    def _update_or_create_dist_git_pr(
            self, project, pr_id, pr_url, top_commit, title, source_ref
    ):
        # Sadly, pagure does not support editing initial comments of a PR via the API
        # https://pagure.io/pagure/issue/4111
        # Short-term solution: keep adding comments
        # and get updated info about sg PR ID and commit desc
        for pr in project.get_pr_list():

            sg_pr_id_match = project.search_in_pr(
                pr_id=pr.id,
                filter_regex=DG_PR_COMMENT_KEY_SG_PR + r":\s*(\d+)",
                reverse=True,
                description=True,
            )
            if not sg_pr_id_match:
                logger.debug(f"No automation comment found in dist-git PR: {pr.id}.")
                continue

            sg_pr_id = sg_pr_id_match[1]
            if sg_pr_id_match[1] != str(pr_id):
                logger.debug(
                    f"Dist-git PR `{pr.id}` does not match " f"source-git PR `{pr_id}`."
                )
                continue

            commit_match = project.search_in_pr(
                pr_id=pr.id,
                filter_regex=DG_PR_COMMENT_KEY_SG_COMMIT + r":\s*(\d+)",
                reverse=True,
                description=True,
            )
            if not commit_match:
                logger.debug(
                    f"Dist-git PR `{pr.id}` does not contain top-commit of the "
                    f"source-git PR `{pr_id}`."
                )
                continue

            logger.debug(f"Adding a new comment with update to existing PR.")
            msg = (
                f"New changes were pushed to the upstream pull request\n\n"
                f"[{DG_PR_COMMENT_KEY_SG_PR}: {pr_id}]({pr_url})\n"
                f"{DG_PR_COMMENT_KEY_SG_COMMIT}: {top_commit}"
            )
            # FIXME: consider storing the data above as a git note of the top commit
            project.change_token(self.pagure_package_token)
            project.pr_comment(pr.id, msg)
            logger.info("new comment added on PR %s", sg_pr_id)
            break
        else:
            logger.debug(f"Matching dist-git PR not found => creating a new one.")
            msg = (
                f"This pull request contains changes from upstream "
                f"and is meant to integrate them into Fedora\n\n"
                f"[{DG_PR_COMMENT_KEY_SG_PR}: {pr_id}]({pr_url})\n"
                f"{DG_PR_COMMENT_KEY_SG_COMMIT}: {top_commit}"
            )
            # This pagure call requires token from the package's FORK
            project_fork = project.get_fork()
            project_fork.change_token(self.pagure_fork_token)
            dist_git_pr_id = project_fork.pr_create(
                title=f"[source-git] {title}",
                body=msg,
                source_branch=source_ref,
                target_branch="master",
            ).id
            logger.info(f"PR created: {dist_git_pr_id}")

    def clean(self):
        while self._tempdirs:
            tempdir = self._tempdirs.pop()
            logger.debug(f"Cleaning: {tempdir}")
            shutil.rmtree(tempdir)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.clean()
