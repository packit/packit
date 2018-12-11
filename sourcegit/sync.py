import json
import logging
import os
import shutil
import tempfile
from functools import lru_cache

import git

from onegittorulethemall.services.pagure import PagureService
from sourcegit.constants import dg_pr_key_sg_commit, dg_pr_key_sg_pr
from sourcegit.transformator import Transformator, get_package_mapping
from sourcegit.utils import commits_to_nice_str

logger = logging.getLogger(__name__)


class Synchronizer:
    def __init__(self) -> None:
        self._tempdirs = []

    def sync_using_fedmsg_dict(self, fedmsg_dict):
        """
        Sync the pr to the dist-git.

        :param fedmsg_dict: dict, fedmsg of a newly opened PR
        """

        try:
            msg_id = fedmsg_dict["msg_id"]
            nice_msg = json.dumps(fedmsg_dict, indent=4)
            logger.debug(f"Processing fedmsg:\n{nice_msg}")
            return self.sync(
                target_url=fedmsg_dict["msg"]["pull_request"]["base"]["repo"]["html_url"],
                target_ref=fedmsg_dict["msg"]["pull_request"]["base"]["ref"],
                source_url=fedmsg_dict["msg"]["pull_request"]["head"]["repo"]["html_url"],
                source_ref=fedmsg_dict["msg"]["pull_request"]["head"]["ref"],
                top_commit=fedmsg_dict["msg"]["pull_request"]["head"]["sha"],
                pr_id=fedmsg_dict["msg"]["pull_request"]["number"],
                title=fedmsg_dict["msg"]["pull_request"]["title"],
                pr_url=fedmsg_dict["msg"]["pull_request"]["html_url"],
            )
        except Exception as ex:
            logger.warning(f"Error on processing a msg {msg_id}")
            logger.debug(ex)
            return None

    def sync(
            self,
            source_url,
            target_url,
            source_ref,
            target_ref,
            top_commit,
            pr_id,
            pr_url,
            title,
    ):
        """
        synchronize selected source-git pull request to respective downstream dist-git repo via a pagure pull request

        :param source_url:
        :param target_url:
        :param source_ref:
        :param target_ref:
        :param top_commit: str, commit hash of the top commit in source-git PR
        :param pr_id:
        :param pr_url:
        :param title:
        :return:
        """

        repo = self.get_repo(url=target_url)
        self.checkout_pr(repo=repo, pr_id=pr_id)

        try:
            package_config = get_package_mapping()[target_url]
        except KeyError:
            logger.info("no source-git mapping for project %s", target_url)
            return

        # FIXME: branch name should be tied to the sg PR, so something like this: f"source-git-{pr_id}"
        with Transformator(
                url=target_url, repo=repo, branch=repo.active_branch, **package_config
        ) as t:
            t.clone_dist_git_repo()

            dist_git_new_branch = t.dist_git_repo.create_head(source_ref)
            dist_git_new_branch.checkout()

            t.create_archive()
            t.copy_redhat_content_to_dest_dir()
            patches = t.create_patches()
            t.add_patches_to_specfile(patch_list=patches)
            t.repo.index.write()

            commits = t.get_commits_to_upstream(upstream=target_ref)
            commits_nice_str = commits_to_nice_str(commits)

            logger.debug(f"Commits in source-git PR:\n{commits_nice_str}")

            msg = f"upstream commit: {top_commit}\n\nupstream repo: {target_url}"
            t.commit_distgit(title=title, msg=msg)

            package_name = package_config["package_name"]
            pagure = PagureService(token=self.pagure_token)

            project = pagure.get_project(repo=package_name, namespace="rpms")

            if not project.fork:
                logger.info("Creating a fork.")
                project.fork_create()

            is_push_force = source_ref in project.fork.branches
            t.dist_git_repo.create_remote(
                name="origin-fork", url=project.fork.git_urls["ssh"]
            )
            # I suggest to comment this one while testing when the push is not needed
            t.dist_git_repo.remote("origin-fork").push(
                refspec=source_ref, force=is_push_force
            )

            # Sadly, pagure does not support editing initial comments of a PR via the API
            # https://pagure.io/pagure/issue/4111
            # Short-term solution: keep adding comments and get updated info about sg PR ID and commit desc
            for pr in project.pr_list():
                dg_pr_id = pr["id"]
                # let's save a few queries by passing the pr_info dict
                sg_pr_id = project.get_sg_pr_id(dg_pr_id, pr_info=pr)
                commit = project.get_sg_top_commit(dg_pr_id, pr_info=pr)
                if sg_pr_id and commit:
                    if sg_pr_id == pr_id:
                        # yep, we got it, this is the right PR (if sg & dg are 1:1 and not n:1)
                        msg = (f"New changes were pushed to the upstream pull request\n\n"
                               f"[{dg_pr_key_sg_pr}: {pr_id}]({pr_url})\n"
                               f"{dg_pr_key_sg_commit}: {top_commit}")
                        # FIXME: consider storing the data above as a git note of the top commit
                        project.pagure.change_token(self.pagure_edit_token)
                        project.pr_comment(dg_pr_id, msg)
                        logger.info("new comment added on PR %s", sg_pr_id)
                        break
            else:
                msg = (f"This pull request contains changes from upstream "
                       f"and is meant to integrate them into Fedora\n\n"
                       f"[{dg_pr_key_sg_pr}: {pr_id}]({pr_url})\n"
                       f"{dg_pr_key_sg_commit}: {top_commit}")
                dist_git_pr_id = project.fork.pr_create(
                    title=f"[source-git] {title}",
                    body=msg,
                    source_branch=source_ref,
                    target_branch="master",
                )["id"]
                logger.info(f"PR created: {dist_git_pr_id}")

    @property
    @lru_cache()
    def pagure_token(self):
        return os.environ["PAGURE_TOKEN"]

    @property
    @lru_cache()
    def pagure_edit_token(self):
        return os.environ["PAGURE_EDIT_TOKEN"]

    @lru_cache()
    def get_repo(self, url, directory=None):
        if not directory:
            tempdir = tempfile.mkdtemp()
            self._tempdirs.append(tempdir)
            directory = tempdir

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

    def clean(self):
        while self._tempdirs:
            tempdir = self._tempdirs.pop()
            logger.debug(f"Cleaning: {tempdir }")
            shutil.rmtree(tempdir)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.clean()
