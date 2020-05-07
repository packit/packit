# MIT License
#
# Copyright (c) 2018-2020 Red Hat, Inc.

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
"""
Processing RPM spec file patches.
"""
import datetime
import logging
from itertools import islice
from pathlib import Path
from typing import List, Tuple, Optional

import git

from packit.constants import DATETIME_FORMAT
from packit.local_project import LocalProject
from packit.utils import is_a_git_ref, run_command

logger = logging.getLogger(__name__)


class PatchGenerator:
    """
    Generate .patch files from git
    """

    def __init__(self, lp: LocalProject):
        self.lp = lp

    def are_child_commits_contained(self, git_ref: str) -> bool:
        r"""
        Magic begins here.

        `git format-patch` produces patches which cannot be applied when commits,
        in front of a git ref, have parents behind:

        * | | | | | | | |   ea500ac513 (tag: v245) Merge pull request #15...
        |\ \ \ \ \ \ \ \ \
        | * | | | | | | | | 0d5aef3eb5 hwdb: update for v245
        | | |_|_|_|_|_|/ /
        | |/| | | | | | |
        * | | | | | | | | 03985d069b NEWS: final contributor update for v245

        In this example, you can see that ea500 is tagged with 245 and
        is a merge commit. The additional lines mean that child commits of v245
        have parents behind v245 which means that `git format-patch` may
        create patches which may not able able to be applied.

        This method detects the situation described above.

        :param git_ref: git ref to check
        :return: yes if all child commits of the selected git ref are contained
                 within the set of git_ref children commits
        """
        commits = self.get_commits_since_ref(
            git_ref, add_upstream_head_commit=True, no_merge_commits=False
        )
        for commit in islice(commits, 1, None):  # 0 = upstream, don't check that one
            for parent_commit in commit.parents:
                if parent_commit not in commits:
                    logger.info(f"Commit {commit!r} has a parent behind {git_ref!r}.")
                    return False
        logger.debug(f"All commits are contained on top of {git_ref!r}.")
        return True

    @staticmethod
    def linearize_history(git_ref: str):
        r"""
        Transform complex git history into a linear one starting from a selected git ref.

        Change this:
        * | | | | | | | |   ea500ac513 (tag: v245) Merge pull request #15...
        |\ \ \ \ \ \ \ \ \
        | * | | | | | | | | 0d5aef3eb5 hwdb: update for v245
        | | |_|_|_|_|_|/ /
        | |/| | | | | | |
        * | | | | | | | | 03985d069b NEWS: final contributor update for v245

        Into this:
        * 0d5aef3eb5 hwdb: update for v245
        * 03985d069b NEWS: final contributor update for v245
        """
        logger.info(
            "When git history is too complex with merge commits having parents \n"
            "across a wide range, git is known to produce patches which cannot be applied. \n"
            "Therefore we are going to make the history linear on a dedicated branch \n"
            "to make sure the patches will be able to be applied."
        )
        current_time = datetime.datetime.now().strftime(DATETIME_FORMAT)
        target_branch = f"packit-patches-{current_time}"
        logger.info(f"Switch branch to {target_branch!r}.")
        run_command(["git", "checkout", "-B", target_branch])
        target = f"{git_ref}..HEAD"
        logger.debug(f"Linearize history {target}.")
        # https://stackoverflow.com/a/17994534/909579
        # With this command we will rewrite git history of our newly created branch
        # by dropping the merge commits and setting parent commits to those from target branch
        # this means we will drop the reference from which we are merging
        # filter branch passes these to cut:
        #   ` -p 61f3e897f13101f29fb8027e8839498a469ad58e`
        #   ` -p b7cf4b4ef5d0336443f21809b1506bc4a8aa75a9 -p 257188f80ce1a083e3a88b679b898a7...`
        # so we will keep the first parent and drop all the others
        run_command(
            [
                "git",
                "filter-branch",
                "-f",
                "--parent-filter",
                'cut -f 2,3 -d " "',
                target,
            ],
            # git prints nasty warning when filter-branch is used that it's dangerous
            # this env var prevents it from prints
            env={"FILTER_BRANCH_SQUELCH_WARNING": "1"},
        )

    def create_patches(
        self,
        git_ref: str,
        destination: str,
        files_to_ignore: Optional[List[str]] = None,
    ) -> List[Tuple[Path, str]]:
        """
        Create patches from git commits.

        :param git_ref: start processing commits from this till HEAD
        :param destination: place the patch files here
        :param files_to_ignore: list of files to ignore when creating patches
        :return: [(patch_path, msg)] list of created patches (tuple of the file path and commit msg)
        """
        contained = self.are_child_commits_contained(git_ref)
        if not contained:
            self.linearize_history(git_ref)

        patch_list = []

        try:
            commits = self.get_commits_since_ref(
                git_ref, add_upstream_head_commit=False
            )
            git_f_p_cmd = [
                "git",
                "format-patch",
                "--output-directory",
                f"{destination}",
                git_ref,
                "--",
                ".",
            ] + [f":(exclude){file_to_ignore}" for file_to_ignore in files_to_ignore]
            git_format_patch_out = run_command(
                cmd=git_f_p_cmd, cwd=self.lp.working_dir, output=True, decode=True,
            ).strip()

            if git_format_patch_out:
                patches = {
                    patch_name: Path(patch_name).read_text()
                    for patch_name in git_format_patch_out.split("\n")
                }
                for commit in commits:
                    for patch_name, patch_content in patches.items():
                        # `git format-patch` usually creates one patch for a merge commit,
                        # so some commits won't be covered by a dedicated patch file
                        if commit.hexsha in patch_content:
                            logger.debug(f"[{patch_name}] {commit.summary}")
                            msg = (
                                f"{commit.summary}\n"
                                f"Author: {commit.author.name} <{commit.author.email}>"
                            )
                            patch_list.append((Path(patch_name), msg))
                            break
            else:
                logger.warning(f"No patches between {git_ref!r} and {self.lp.ref!r}")

            return patch_list
        finally:
            if not contained:
                # check out the previous branch
                run_command(["git", "checkout", "-", "--"])
                # we could also delete the newly created branch,
                # but let's not do that so that user can inspect it

    def get_commits_since_ref(
        self,
        git_ref: str,
        add_upstream_head_commit: bool = True,
        no_merge_commits: bool = True,
    ) -> List[git.Commit]:
        """
        Return a list of different commits between HEAD and selected git_ref

        :param git_ref: get commits since this git ref
        :param add_upstream_head_commit: add also upstream rev/tag commit as a first value
        :param no_merge_commits: do not include merge commits in the list if True
        :return: list of commits (last commit on the current branch.).
        """

        if is_a_git_ref(repo=self.lp.git_repo, ref=git_ref):
            upstream_ref = git_ref
        else:
            upstream_ref = f"origin/{git_ref}"
            if upstream_ref not in self.lp.git_repo.refs:
                raise Exception(
                    f"Upstream {upstream_ref!r} branch nor {git_ref!r} tag not found."
                )

        commits = list(
            self.lp.git_repo.iter_commits(
                rev=f"{git_ref}..{self.lp.ref}",
                reverse=True,
                no_merges=no_merge_commits,  # do not include merge commits in the list
            )
        )
        if add_upstream_head_commit:
            commits.insert(0, self.lp.git_repo.commit(upstream_ref))

        logger.debug(f"Delta ({upstream_ref}..{self.lp.ref}): {len(commits)}")
        return commits
