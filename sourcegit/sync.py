import logging
import os
import shutil
import tempfile
from functools import lru_cache

import git

from sourcegit.transformator import Transformator, get_package_mapping

logger = logging.getLogger(__name__)


class Synchronizer:
    def __init__(self) -> None:
        self._tempdirs = []

    def sync_using_fedmsg_dict(self, fedmsg_dict):
        """
        Sync the pr to the dist-git.

        :param fedmsg_dict: dict, fedmsg of a newly opened PR
        """
        return self.sync(
            target_url=fedmsg_dict["msg"]["pull_request"]["base"]["repo"]["html_url"],
            target_ref=fedmsg_dict["msg"]["pull_request"]["base"]["ref"],
            source_url=fedmsg_dict["msg"]["pull_request"]["head"]["repo"]["html_url"],
            source_ref=fedmsg_dict["msg"]["pull_request"]["head"]["ref"],
            top_commit=fedmsg_dict["msg"]["pull_request"]["head"]["sha"],
            pr_id=fedmsg_dict["msg"]["pull_request"]["number"],
        )

    def sync(self, source_url, target_url, source_ref, target_ref, top_commit, pr_id):

        repo = self.get_repo(url=target_url)
        self.checkout_pr(repo=repo, pr_id=pr_id)

        package_config = get_package_mapping().get(target_url, {})

        with Transformator(
                url=target_url, repo=repo, branch=repo.active_branch, **package_config
        ) as t:
            t.create_archive()
            t.copy_redhat_content_to_dest_dir()
            patches = t.create_patches()
            t.add_patches_to_specfile(patch_list=patches)

            # Commit
            # Force push
            # Create a pr in dist-git (fork if needed)

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
