# MIT License
#
# Copyright (c) 2020 Red Hat, Inc.

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
from typing import List, Optional, Dict

import git
import yaml
from packit.exceptions import PackitException

from packit.constants import DATETIME_FORMAT
from packit.git_utils import get_metadata_from_message
from packit.local_project import LocalProject
from packit.utils.commands import run_command
from packit.utils.repo import is_a_git_ref

logger = logging.getLogger(__name__)


class PatchMetadata:
    def __init__(
        self,
        name: Optional[str] = None,
        path: Optional[Path] = None,
        location_in_specfile: Optional[str] = None,
        description: Optional[str] = None,
        commit: Optional[git.Commit] = None,
        present_in_specfile: bool = False,
        ignore: bool = False,
        squash_commits: bool = False,
        no_prefix: bool = False,
        metadata_defined: bool = None,
    ) -> None:
        """
        Metadata about patch files and relation to the respective commit.

        :param name: name of the patch file
        :param path: Path of the patch file
        :param location_in_specfile: index of the patch in spec-file
        :param description: will be attached as a comment above path in spec-file
                            (if present_in_specfile=False)
        :param commit: git.Commit relevant to this patch file
        :param present_in_specfile: if the patch is already in the spec-file
                                    and we don't need to add it there
        :param ignore: We don't want to process this commit
                        when we convert source-git commits to patches.
                        This patch will be skipped.
        :param squash_commits: squash commits into a single patch file
                               until next commits with squash_commits=True
                               (git-am patches do this)
        :param no_prefix: do not prepend a/ and b/ when generating the patch file
        :param metadata_defined: are any of the metadata defined in a commit message
        """
        self.name = name
        self.path = path
        self.location_in_specfile = location_in_specfile
        self.description = description
        self.commit = commit
        self.present_in_specfile = present_in_specfile
        self.ignore = ignore
        self.squash_commits = squash_commits
        self.no_prefix = no_prefix
        # this is set during PatchMetadata.from_commit()
        self.metadata_defined = metadata_defined

    @property
    def specfile_comment(self) -> str:
        if self.commit:
            comment = (
                f"{self.commit.summary}\n"
                f"Author: {self.commit.author.name} <{self.commit.author.email}>"
            )
        else:
            comment = f'Patch "{self.name}"'
        if self.description:
            comment += f"\n{self.description}"
        return comment

    @property
    def commit_message(self) -> str:
        msg = f"Apply {self.name}\n"

        if self.name:
            msg += f"\npatch_name: {self.name}"

        if self.location_in_specfile:
            msg += f"\nlocation_in_specfile: {self.location_in_specfile}"

        if self.description:
            msg += f"\ndescription: {self.description}"

        if self.present_in_specfile:
            msg += "\npresent_in_specfile: true"

        if self.ignore:
            msg += "\nignore: true"

        if self.squash_commits:
            msg += "\nsquash_commits: true"

        if self.no_prefix:
            msg += "\nno_prefix: true"

        return msg

    @staticmethod
    def from_commit(
        commit: git.Commit, patch_path: Optional[Path] = None
    ) -> "PatchMetadata":
        """
        Load PatchMetadata from an existing git.Commit

        @param commit: the git.Commit to load the metadata from
        @param patch_path: optional Path to an existing patch file present on the disk
        @return: PatchMetadata instance
        """
        metadata = get_metadata_from_message(commit) or {}
        metadata_defined = False
        if metadata:
            logger.debug(
                f"Commit {commit.hexsha:.8} metadata:\n"
                f"{yaml.dump(metadata, indent=4, default_flow_style=False)}"
            )
            metadata_defined = True
        else:
            logger.debug(f"Commit {commit.hexsha:.8} does not contain any metadata.")

        name = metadata.get("patch_name")
        if patch_path:
            if name:
                new_path = patch_path.parent / name
                logger.debug(f"Renaming the patch: {patch_path.name} -> {new_path}")
                patch_path.rename(new_path)
                patch_path = new_path
            else:
                name = patch_path.name

        return PatchMetadata(
            name=name,
            path=patch_path,
            description=metadata.get("description"),
            present_in_specfile=metadata.get("present_in_specfile"),
            location_in_specfile=metadata.get("location_in_specfile"),
            ignore=metadata.get("ignore"),
            commit=commit,
            squash_commits=metadata.get("squash_commits"),
            no_prefix=metadata.get("no_prefix"),
            metadata_defined=metadata_defined,
        )

    def __repr__(self):
        return f"Patch(name={self.name}, commit={self.commit})"


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

    def run_git_format_patch(
        self,
        destination: str,
        files_to_ignore: List[str],
        ref_or_range: str,
        no_prefix: bool = False,
    ):
        """
        run `git format-patch $ref_or_range` in self.local_project.working_dir

        :param destination: place the patches here
        :param files_to_ignore: ignore changes in these files
        :param ref_or_range: [ <since> | <revision range> ]:
               1. A single commit, <since>, specifies that the commits leading to the tip of the
                  current branch that are not in the history that leads to the <since> to be
                  output.

               2. Generic <revision range> expression (see "SPECIFYING REVISIONS" section in
                  gitrevisions(7)) means the commits in the specified range.
        :param no_prefix: prefix is the leading a/ and b/ - format-patch does this by default
        :return: str, git format-patch output: new-line separated list of patch names
        """
        git_f_p_cmd = ["git", "format-patch", "--output-directory", f"{destination}"]
        if no_prefix:
            git_f_p_cmd.append("--no-prefix")
        git_f_p_cmd += [
            ref_or_range,
            "--",
            ".",
        ] + [f":(exclude){file_to_ignore}" for file_to_ignore in files_to_ignore]
        return run_command(
            cmd=git_f_p_cmd,
            cwd=self.lp.working_dir,
            output=True,
            decode=True,
        ).strip()

    def process_patches(
        self,
        patches: Dict[str, bytes],
        commits: List[git.Commit],
        destination: str,
        files_to_ignore: List[str] = None,
    ):
        """
        Pair commits (in a source-git repo) with a list patches generated with git-format-patch.

        Pairing is done using commit.hexsha (which is always present in the patch file).

        patch_list (provided List) is then mutated by appending PatchMetadata using
        the paired information: commit and a path to the patch file.

        :param patches: Dict: commit hexsha -> patch content
        :param commits: list of commits we created the patches from
        :param destination: place the patch files here
        :param files_to_ignore: list of files to ignore when creating patches
        """
        patch_list: List[PatchMetadata] = []
        for commit in commits:
            # commit.size doesn't work since even an empty commit is size > 0 (287)
            if not commit.stats.files:
                # this patch is empty - rpmbuild is okay with empty patches (!)
                logger.debug(f"commit {commit} is empty")
                patch = PatchMetadata.from_commit(commit=commit)
                if not patch.present_in_specfile:
                    # it's empty and not present in spec file
                    # nothing to do here
                    continue
                if not patch.name:
                    raise PackitException(
                        f"Empty commit {commit} is referencing a patch which is present in spec"
                        " file but the name is not defined in the commit metadata"
                        " - please define it."
                    )
                patch_list.append(patch)

                # we need to create it since `git format-patch` won't
                Path(destination).joinpath(patch.name).write_text("")
                logger.info(f"created empty patch {patch.path}")
                continue
            for patch_name, patch_content in patches.items():
                # `git format-patch` usually creates one patch for a merge commit,
                # so some commits won't be covered by a dedicated patch file
                if commit.hexsha.encode() in patch_content:
                    path = Path(patch_name)
                    patch_metadata = PatchMetadata.from_commit(
                        commit=commit, patch_path=path
                    )

                    if patch_metadata.ignore:
                        logger.debug(
                            f"[IGNORED: {patch_metadata.name}] {commit.summary}"
                        )
                    else:
                        logger.debug(f"[{patch_metadata.name}] {commit.summary}")
                        if patch_metadata.no_prefix:
                            # sadly, we have work to do, the original patch is no good:
                            # format-patch by default generates patches with prefixes a/ and b/
                            # no-prefix means we don't want those: we need create the patch, again
                            # https://github.com/packit/dist-git-to-source-git/issues/85#issuecomment-698827925
                            git_f_p_out = self.run_git_format_patch(
                                destination,
                                files_to_ignore,
                                f"{commit}^..{commit}",
                                no_prefix=True,
                            )
                            patch_list.append(
                                PatchMetadata.from_commit(
                                    commit=commit, patch_path=Path(git_f_p_out)
                                )
                            )
                        else:
                            patch_list.append(patch_metadata)
                    break
        return patch_list

    @staticmethod
    def process_git_am_style_patches(
        patch_list: List[PatchMetadata],
    ):
        """
        When using `%autosetup -S git_am`, there is a case
        where a single patch file contains multiple commits.
        This is problematic for us since only the leading commit
        is annotated. To make matters worse, we also want to support the fact
        that leading commits would not follow the scheme - make contributions easier.

        In this case, we need to:
        1. detect this is happening - a commit has `squash_commits=True`
        2. process every commit, reversed (patches[-1] is HEAD)
        3. append commits to a single patch until `squash_commits=True`
        4. return new patch list
        """
        if not any(commit.squash_commits for commit in patch_list):
            logger.debug(
                "any of the commits has squash_commits=True, not the git-am style of patches"
            )
            return patch_list

        new_patch_list: List[PatchMetadata] = []

        prepend_patches = ""
        # this iterator is being reused in both cycles below
        # first we process the commits before first squash_commits and
        # prepend them before the first top_commit
        # while the second cycle goes through the rest of the patches
        reversed_patch_list = reversed(patch_list)
        while True:
            # iterate through the list until squash_commits=True is found
            # prepend those commits to the first top patch
            patch = next(reversed_patch_list)
            if patch.squash_commits:
                # top_patch is a leading commit with squash_commits=True
                top_patch = patch
                break
            logger.debug(f"Prepending patch {patch}.")
            prepend_patches = patch.path.read_text() + prepend_patches
            patch.path.unlink()
        if prepend_patches:
            top_patch.path.write_text(top_patch.path.read_text() + prepend_patches)

        while True:
            if (
                patch.squash_commits
                or patch.present_in_specfile
                or patch.metadata_defined
            ):
                top_patch = patch
                new_patch_list.append(top_patch)
                logger.debug(f"Top commit in a patch: {top_patch}.")
            else:
                logger.debug(f"Appending commit {patch} to {top_patch}.")
                top_patch.path.write_text(
                    patch.path.read_text() + top_patch.path.read_text()
                )
                patch.path.unlink()
            # we are draining rest of the iterator here
            try:
                patch = next(reversed_patch_list)
            except StopIteration:
                break

        return new_patch_list

    def create_patches(
        self,
        git_ref: str,
        destination: str,
        files_to_ignore: Optional[List[str]] = None,
    ) -> List[PatchMetadata]:
        """
        Create patches from git commits.

        :param git_ref: start processing commits from this till HEAD
        :param destination: place the patch files here
        :param files_to_ignore: list of files to ignore when creating patches
        :return: [PatchMetadata, ...] list of patches
        """
        files_to_ignore = files_to_ignore or []
        contained = self.are_child_commits_contained(git_ref)
        if not contained:
            self.linearize_history(git_ref)

        patch_list: List[PatchMetadata] = []

        try:
            commits = self.get_commits_since_ref(
                git_ref, add_upstream_head_commit=False
            )
            # this is a string, separated by new-lines, with the names of patch files
            git_format_patch_out = self.run_git_format_patch(
                destination, files_to_ignore, git_ref
            )

            if git_format_patch_out:
                patches: Dict[str, bytes] = {
                    # we need to read bytes since we cannot decode whatever is inside patches
                    patch_name: Path(patch_name).read_bytes()
                    for patch_name in git_format_patch_out.split("\n")
                }
                patch_list = self.process_patches(
                    patches, commits, destination, files_to_ignore
                )
                patch_list = self.process_git_am_style_patches(patch_list)
            else:
                logger.info(f"No patches between {git_ref!r} and {self.lp.ref!r}")

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
                raise PackitException(
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
