# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import git
import logging
from typing import Optional

from rebasehelper.specfile import SpecFile
from packit.config import Config, PackageConfig
from packit.exceptions import PackitException
from packit.local_project import LocalProject

logger = logging.getLogger(__name__)


class PackitRepositoryBase:
    # mypy complains when this is a property
    local_project: LocalProject

    def __init__(self, config: Config, package_config: PackageConfig) -> None:
        self.config = config
        self.package_config = package_config
        self._specfile = None

    @property
    def specfile(self) -> SpecFile:
        """
        :return: an instance of SpecFile
        """
        raise NotImplementedError

    @property
    def specfile_path(self) -> Optional[str]:
        """
        :return: a path to a Spec file
        """
        raise NotImplementedError

    def create_branch(
        self, branch_name: str, base: str = "HEAD", setup_tracking: bool = False
    ) -> git.Head:
        """
        Create a new git branch in dist-git

        :param branch_name: name of the branch to check out and fetch
        :param base: we base our new branch on this one
        :param setup_tracking: set up remote tracking
               (exc will be raised if the branch is not in the remote)
        :return the branch which was just created
        """
        # it's not an error if the branch already exists
        origin = self.local_project.git_repo.remote("origin")
        head = self.local_project.git_repo.create_head(branch_name, commit=base)

        if setup_tracking:
            if branch_name in origin.refs:
                remote_ref = origin.refs[branch_name]
            else:
                raise PackitException("Remote origin doesn't have ref %s" % branch_name)
            # this is important to fedpkg: build can't find the tracking branch otherwise
            head.set_tracking_branch(remote_ref)

        return head

    def checkout_branch(self, git_ref: str):
        """
        Perform a `git checkout`

        :param git_ref: ref to check out
        """
        if git_ref in self.local_project.git_repo.heads:
            head = self.local_project.git_repo.heads[git_ref]
        else:
            raise PackitException(f"Branch {git_ref} does not exist")
        head.checkout()

    def commit(self, title: str, msg: str, prefix: str = "[packit] ") -> None:
        """
        Perform `git add -A` and `git commit`
        """
        logger.debug("About to add all & commit")
        main_msg = f"{prefix}{title}"
        # add files to index in case some are untracked
        # untracked files don't make a git repo dirty, unless they are staged
        self.local_project.git_repo.git.add("-A")
        if not self.local_project.git_repo.is_dirty():
            raise PackitException(
                "No changes are present in the dist-git repo: nothing to commit."
            )
        self.local_project.git_repo.index.write()
        commit_args = ["-s", "-m", main_msg]
        if msg:
            commit_args += ["-m", msg]
        # TODO: attach git note to every commit created
        # TODO: implement cleaning policy: once the PR is closed (merged/refused), remove the branch
        #       make this configurable so that people know this would happen, don't clean by default
        #       we should likely clean only merged PRs by default
        # TODO: implement signing properly: we need to create a cert for the bot,
        #       distribute it to the container, prepare git config and then we can start signing
        # TODO: make -s configurable
        self.local_project.git_repo.git.commit(*commit_args)
