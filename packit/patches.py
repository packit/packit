# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Processing RPM spec file patches.
"""
import datetime
import email
import logging
import re
import tempfile
from itertools import islice
from pathlib import Path
from typing import Optional

import git
import yaml

from packit.constants import DATETIME_FORMAT, PATCH_META_TRAILER_TOKENS
from packit.exceptions import PackitException, PackitGitException
from packit.local_project import LocalProject
from packit.utils.commands import run_command
from packit.utils.repo import get_metadata_from_message, git_patch_ish, is_a_git_ref

logger = logging.getLogger(__name__)


def git_format_patch(
    working_dir: Path,
    destination: str,
    files_to_ignore: list[str],
    ref_or_range: str,
    no_prefix: bool = False,
):
    """
    run `git format-patch $ref_or_range` in working_dir

    :param working_dir: Path where to run the command.
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
        cwd=working_dir,
        output=True,
    ).stdout.strip()


def git_interpret_trailers(patch: str) -> str:
    """Run 'git interpret-trailers' on 'patch' and return the output.

    We don't use --parse/--unfold to unfold multiline values per RFC822
    because we use YAML block scalars for multiline trailer values.

    Args:
        patch: Path of the patch.

    Returns:
        The output of the command.
    """
    cmd = ["git", "interpret-trailers", "--only-input", "--only-trailers", patch]
    return run_command(cmd=cmd, cwd=Path.cwd(), output=True).stdout


def remove_prefixes(patch: Path):
    """Remove source or destination prefixes from a patch file

    Args:
        patch: Path of the patch file.
    """
    logger.debug(f"Remove prefixes from {patch}.")
    content = patch.read_text()
    content = re.sub(
        r"^(diff .+) a/(.+) b/(.+)$", r"\1 \2 \3", content, flags=re.MULTILINE
    )
    content = re.sub(r"^(---) a/(.+)$", r"\1 \2", content, flags=re.MULTILINE)
    content = re.sub(r"^(\+\+\+) b/(.+)$", r"\1 \2", content, flags=re.MULTILINE)
    patch.write_text(content)


def commit_message(
    patch: Path,
    strip_subject_prefix: Optional[str] = None,
    strip_trailers: Optional[str] = None,
) -> str:
    """Read the commit message from a file

    The file can be a text file with the commit message or a patch file produced by
    'git format-patch'.

    If specified, strip any '[<strip_subject_prefix>]' prefix from the subject line
    and the git trailers.

    Args:
        patch: Path of the file.
        strip_subject_prefix: Strip this prefix from subject lines.
        strip_trailers: Strip these trailer lines from the end of the commit message.

    Returns:
        The commit message: subject and body, separated by an empty line.
    """
    message = email.message_from_bytes(patch.read_bytes())
    subject = message["Subject"]
    # The file only contains the commit message.
    if not subject:
        subject, _, body = message.get_payload().partition("\n\n")
    # The file is a patch file generated by format-patch.
    else:
        body, sep, _ = message.get_payload().partition("\n---\n")
        if not sep:
            body = ""

    if strip_subject_prefix:
        # Strip [<subject_prefix>] or [<subject_prefix> n/m]
        subject = re.sub(
            r"^\[" + strip_subject_prefix + r"( \d+/\d+)?\] (.+)$", r"\2", subject
        )

    if strip_trailers:
        body = body.partition(strip_trailers)[0]

    empty_line = "\n\n" if body else ""
    return f"{subject}{empty_line}{body}".strip()


class PatchMetadata:
    """
    Metadata about patch files and relation to the respective commit.

    Attributes:
        name: name of the patch file (patch_name is the actual metadata key)
        path: Path of the patch file
        description: will be attached as a comment above Patch spec definition
                     (if present_in_specfile=False)
        commit: git.Commit relevant to this patch file
        present_in_specfile: if the patch is already in the spec-file
                             and we don't need to add it there
        ignore: this patch will not be processed.
        squash_commits: squash commits into a single patch file
                        until next commits with squash_commits=True
                        (git-am patches do this)
        patch_id: the number from definition PatchNNNN in the spec
        no_prefix: do not prepend a/ and b/ when generating the patch file
        metadata_defined: are any of the metadata defined in a commit message
    """

    def __init__(
        self,
        name: Optional[str] = None,
        path: Optional[Path] = None,
        description: Optional[str] = None,
        commit: Optional[git.Commit] = None,
        present_in_specfile: bool = False,
        ignore: bool = False,
        squash_commits: bool = False,
        patch_id: Optional[int] = None,
        no_prefix: bool = False,
        metadata_defined: bool = False,
    ) -> None:
        self.name = name
        self.path = path
        self.description = description
        self.commit = commit
        self.present_in_specfile = present_in_specfile
        self.ignore = ignore
        self.squash_commits = squash_commits
        self.patch_id = patch_id
        self.no_prefix = no_prefix
        # this is set during PatchMetadata.from_commit()
        self.metadata_defined = metadata_defined

    def __eq__(self, other) -> bool:
        return (
            self.name == other.name
            and self.path == other.path
            and self.description == other.description
            and self.commit == other.commit
            and self.present_in_specfile == other.present_in_specfile
            and self.ignore == other.ignore
            and self.squash_commits == other.squash_commits
            and self.patch_id == other.patch_id
            and self.no_prefix == other.no_prefix
            and self.metadata_defined == other.metadata_defined
        )

    @property
    def specfile_comment(self) -> str:
        if self.description:
            comment = self.description
        elif self.commit:
            comment = (
                f"{self.commit.summary}\n"
                f"Author: {self.commit.author.name} <{self.commit.author.email}>"
            )
        else:
            comment = f'Patch "{self.name}"'
        return comment

    @property
    def commit_message(self) -> str:
        msg = f"Apply {self.name}\n"

        if self.name:
            msg += f"\npatch_name: {self.name}"

        if self.description:
            msg += f"\ndescription: {self.description}"

        if self.present_in_specfile:
            msg += "\npresent_in_specfile: true"

        if self.ignore:
            msg += "\nignore: true"

        if self.squash_commits:
            msg += "\nsquash_commits: true"

        if self.patch_id is not None:
            msg += f"\npatch_id: {self.patch_id}"

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

        name = metadata.get("patch_name") or (patch_path.name if patch_path else None)

        return PatchMetadata(
            name=name,
            path=patch_path,
            description=metadata.get("description"),
            present_in_specfile=metadata.get("present_in_specfile"),
            ignore=metadata.get("ignore"),
            commit=commit,
            squash_commits=metadata.get("squash_commits"),
            patch_id=metadata.get("patch_id", None),
            no_prefix=metadata.get("no_prefix"),
            metadata_defined=metadata_defined,
        )

    @staticmethod
    def from_git_trailers(commit: git.Commit) -> "PatchMetadata":
        """Read patch metadata from a commit's git trailers

        Args:
            commit: Commit object to read patch metadata from.

        Returns:
            Patch metadata read.
        """
        with tempfile.NamedTemporaryFile(mode="w+t") as fp:
            fp.write(commit.message)
            fp.flush()
            return PatchMetadata.from_patch(fp.name)

    @staticmethod
    def from_patch(patch: str) -> "PatchMetadata":
        """Read patch metadata by parsing Git trailers from a patch file.

        Args:
            patch: Path of a patch file.

        Returns:
            A PatchMetadata object.
        """
        trailers = git_interpret_trailers(patch).strip()
        trailer = ""
        metadata = {}
        for line in trailers.splitlines():
            token = line.partition(": ")[0]
            if token and not token.startswith(" ") and trailer:
                # found ANOTHER trailer, store the previous one
                metadata.update(yaml.safe_load(trailer))
                trailer = ""
            if token in PATCH_META_TRAILER_TOKENS or (
                token.startswith(" ") and trailer
            ):
                # it's OUR token or we're already processing OUR trailer
                trailer += line + "\n"
        metadata.update(yaml.safe_load(trailer) or {})

        patch_path = Path(patch)
        description = metadata.get("Patch-status") or commit_message(
            patch_path, strip_subject_prefix="PATCH", strip_trailers=trailers
        )
        return PatchMetadata(
            name=metadata.get("Patch-name") or patch_path.name,
            path=patch_path,
            description=description.strip(),
            present_in_specfile=metadata.get("Patch-present-in-specfile", False),
            ignore=metadata.get("Ignore-patch", False),
            patch_id=metadata.get("Patch-id"),
            no_prefix=metadata.get("No-prefix", False),
            metadata_defined=bool(metadata),
        )

    def __repr__(self):
        return (
            f"Patch("
            f"name={self.name}, "
            f"path={self.path}, "
            f"description={self.description}, "
            f"commit={self.commit}, "
            f"present_in_specfile={self.present_in_specfile}, "
            f"ignore={self.ignore}, "
            f"squash_commits={self.squash_commits}, "
            f"patch_id={self.patch_id}, "
            f"no_prefix={self.no_prefix}, "
            f"metadata_defined={self.metadata_defined}"
            ")"
        )


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

    def linearize_history(self, git_ref: str) -> str:
        r"""
        Transform complex git history into a linear one starting from a selected git ref.

        Returns the name of the linearized branch.

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
        if self.lp.git_repo.is_dirty():
            raise PackitGitException(
                "The source-git repo is dirty which means we won't be able to do a linear history. "
                "Please commit the changes to resolve the issue. If you are changing the content "
                "of the repository in an action, you can commit those as well."
            )
        current_time = datetime.datetime.now().strftime(DATETIME_FORMAT)
        initial_branch = self.lp.ref
        target_branch = f"packit-patches-{current_time}"
        logger.info(f"Switch branch to {target_branch!r}.")
        ref = self.lp.create_branch(target_branch)
        ref.checkout()
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
        try:
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
                # this env var prevents it from printing
                env={"FILTER_BRANCH_SQUELCH_WARNING": "1"},
                print_live=True,
                cwd=self.lp.working_dir,
            )
        finally:
            # check out the former branch
            self.lp.checkout_ref(initial_branch)
            # we could also delete the newly created branch,
            # but let's not do that so that user can inspect it
        return target_branch

    def process_patches(
        self,
        patches: dict[str, bytes],
        commits: list[git.Commit],
        destination: str,
        files_to_ignore: Optional[list[str]] = None,
    ) -> list[PatchMetadata]:
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
        patch_list: list[PatchMetadata] = []
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
                            # Sadly, we have work to do, the original patch is no good:
                            # 'format-patch' by default generates patches with prefixes a/ and b/.
                            # 'no-prefix' means we don't want those: we need to delete and re-create
                            # the patch without the prefixes.
                            # https://github.com/packit/dist-git-to-source-git/issues/85#issuecomment-698827925
                            path.unlink()
                            git_f_p_out = git_format_patch(
                                self.lp.working_dir,
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

    def process_patches_with_trailers(
        self, patches: list[str]
    ) -> tuple[list[PatchMetadata], bool]:
        """Collect and return patch metadata stored in Git trailers.

        Args:
            patches: List of patch paths as produced by 'git format-patch'
                with the '--output-directory' option.

        Returns:
            A list of PatchMetadata objects and a flag to indicate whether any metadata
            stored in Git trailers was found or not.
        """
        patch_list: list[PatchMetadata] = [
            PatchMetadata.from_patch(patch) for patch in patches
        ]
        used_git_trailers = any(patch.metadata_defined for patch in patch_list)
        if used_git_trailers:
            patch_list = [patch for patch in patch_list if not patch.ignore]
            (remove_prefixes(patch.path) for patch in patch_list if patch.no_prefix)
        return patch_list, used_git_trailers

    @staticmethod
    def squash_by_squash_commits(
        patch_list: list[PatchMetadata],
    ) -> list[PatchMetadata]:
        """Append commits to a single patch until 'squash_commits==True'
        is found.

        Do this after reversing the list of commits, so that they are in a
        newest-to-oldest order, that is HEAD is the first in the list.

        Args:
            patch_list: List of patch metadata objects, corresponding to commits,
                from the oldest to the newest (that is, in the order 'git format-patch'
                produces them)

        Returns:
            List of patch metadata objects, with commits squashed if required.
        """
        logger.warning(
            "Squashing commits by 'squash_commits' metadata. "
            "This mechanism is deprecated. Please, use an "
            "identical 'patch_name' to merge multiple adjacent "
            "commits in a single patch file, instead."
        )

        new_patch_list: list[PatchMetadata] = []

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

        # we need to reverse it back to be consistent with the order
        new_patch_list.reverse()
        return new_patch_list

    @staticmethod
    def squash_by_patch_name(patch_list: list[PatchMetadata]) -> list[PatchMetadata]:
        """Squash adjacent patches if they have identical names.

        Squashing is done by appending the content of a patch to the previous patch
        if the name of the patch matches the name of the previous patch, and removing
        the corresponding PatchMetadata object from the list.

        Note, that renaming the patch files so that their names matches the name
        specified in the metadata is done in 'rename_patches()'.

        Args:
            patch_list: List of PatchMetadata objects, ordered from
                the oldest to the newest commit.

        Returns:
            List of PatchMetadata objects after squashing the patches.

        Raises:
            PackitException if non-adjacent patches have the same name.
        """
        logger.debug("Squashing commits by 'patch_name'.")
        squashed_patch_list: list[PatchMetadata] = []
        seen_patch_names = set()
        for patch in patch_list:
            if squashed_patch_list and squashed_patch_list[-1].name == patch.name:
                logger.debug(
                    f"Appending patch {patch!r} to {squashed_patch_list[-1]!r}."
                )
                squashed_patch_list[-1].path.write_text(
                    squashed_patch_list[-1].path.read_text() + patch.path.read_text()
                )
                patch.path.unlink()
            else:
                if patch.name in seen_patch_names:
                    raise PackitException(
                        f"Non-adjacent patches cannot have the same name: {patch.name}."
                    )
                seen_patch_names.add(patch.name)
                squashed_patch_list.append(patch)
        return squashed_patch_list

    @staticmethod
    def squash_patches(
        patch_list: list[PatchMetadata],
    ) -> list[PatchMetadata]:
        """
        When using `%autosetup -S git_am`, there is a case
        where a single patch file contains multiple commits.
        This is problematic for us since only the leading commit
        is annotated. To make matters worse, we also want to support the fact
        that leading commits would not follow the scheme - make contributions easier.

        In this case, we need to append commits to a single patch, either by looking
        at the 'squash_commits' metadata or by identical 'patch_name'-s, and return
        the new list of patches.

        Args:
            patch_list: List of patch metadata objects, corresponding to commits,
                from the oldest to the newest (that is, in the order 'git format-patch'
                produces them)

        Returns:
            List of patch metadata objects, with commits squashed if required.
        """
        if any(commit.squash_commits for commit in patch_list):
            return PatchGenerator.squash_by_squash_commits(patch_list)
        else:
            return PatchGenerator.squash_by_patch_name(patch_list)

    @staticmethod
    def rename_patches(patch_list: list[PatchMetadata]):
        """Ensure that patch file names match 'patch_name', if defined.

        Args:
            patch_list: A list of PatchMetadata objects.
        """
        for patch in patch_list:
            # Not all patches have a name.
            # Empty patches don't have a path.
            if not (patch.name and patch.path):
                continue
            if patch.name != patch.path.name:
                new_path = patch.path.parent / patch.name
                logger.debug(
                    f"Renaming the patch: {patch.path} -> {new_path}"
                    f"{' (already exists)' if new_path.exists() else ''}"
                )
                patch.path.rename(new_path)
                patch.path = new_path

    @staticmethod
    def undo_identical(
        patch_list: list[PatchMetadata],
        repo: git.Repo,
    ) -> list[PatchMetadata]:
        """
        Remove from patch_list and undo changes of patch files which
        have the same patch-id as their previous version, and so they
        can be considerd identical.

        :param patch_list: List of patches to check.
        :param repo: Git repo to work in.
        :return: A filtered list of patches, with identical patches removed.
        """
        ret: list[PatchMetadata] = []
        for patch in patch_list:
            relative_patch_path = patch.path.relative_to(repo.working_dir)
            logger.debug(f"Processing {relative_patch_path} ...")
            new_patch = str(relative_patch_path) in repo.untracked_files
            if new_patch:
                logger.debug(f"{relative_patch_path} is a new patch")
                ret.append(patch)
                continue

            # patch-id before the change
            prev_patch = repo.git.show(f"HEAD:{relative_patch_path}")
            prev_patch = git_patch_ish(prev_patch)
            # We can't know the encoding of the patch.
            # https://docs.python.org/3/howto/unicode.html#files-in-an-unknown-encoding
            with tempfile.TemporaryFile(mode="w+", errors="surrogateescape") as fp:
                fp.write(prev_patch)
                fp.seek(0)
                prev_patch_id = repo.git.patch_id("--stable", istream=fp).split()[0]
                logger.debug(f"Previous patch-id: {prev_patch_id}")

            # current patch-id
            with open(patch.path) as fp:
                current_patch_id = repo.git.patch_id("--stable", istream=fp).split()[0]
                logger.debug(f"Current patch-id: {current_patch_id}")

            if current_patch_id != prev_patch_id:
                ret.append(patch)
            else:
                # this looks the same, don't change it
                repo.git.checkout("--", relative_patch_path)
        return ret

    def create_patches(
        self,
        git_ref: str,
        destination: str,
        files_to_ignore: Optional[list[str]] = None,
    ) -> list[PatchMetadata]:
        """
        Create patches from git commits.

        :param git_ref: start processing commits from this till HEAD
        :param destination: place the patch files here
        :param files_to_ignore: list of files to ignore when creating patches
        :return: [PatchMetadata, ...] list of patches
        """
        files_to_ignore = files_to_ignore or []
        patch_list: list[PatchMetadata] = []
        contained = self.are_child_commits_contained(git_ref)
        patches_revision_range = f"{git_ref}..HEAD"
        if not contained:
            lin_branch = self.linearize_history(git_ref)
            # we're still on the same branch but want to get patches from the linearized branch
            patches_revision_range = f"{git_ref}..{lin_branch}"

        # this is a string, separated by new-lines, with the names of patch files
        git_format_patch_out = git_format_patch(
            self.lp.working_dir, destination, files_to_ignore, patches_revision_range
        )

        if git_format_patch_out:
            patches: dict[str, bytes] = {
                # we need to read bytes since we cannot decode whatever is inside patches
                patch_name: Path(patch_name).read_bytes()
                for patch_name in git_format_patch_out.split("\n")
            }
            commits = self.get_commits_in_range(patches_revision_range)
            patch_list, used_git_trailers = self.process_patches_with_trailers(
                list(patches)
            )
            if not used_git_trailers:
                patch_list = self.process_patches(
                    patches, commits, destination, files_to_ignore
                )
            patch_list = self.squash_patches(patch_list)
            self.rename_patches(patch_list)
        else:
            logger.info(f"No patches in range {patches_revision_range}")

        return patch_list

    def get_commits_since_ref(
        self,
        git_ref: str,
        add_upstream_head_commit: bool = True,
        no_merge_commits: bool = True,
    ) -> list[git.Commit]:
        """
        Return a list of different commits between HEAD and selected git_ref

        :param git_ref: get commits since this git ref
        :param add_upstream_head_commit: add also upstream rev/tag commit as a first value
        :param no_merge_commits: do not include merge commits in the list if True
        :return: list of commits (last commit on the current branch)
        """
        if is_a_git_ref(repo=self.lp.git_repo, ref=git_ref):
            upstream_ref = git_ref
        else:
            upstream_ref = f"origin/{git_ref}"
            if upstream_ref not in self.lp.git_repo.refs:
                raise PackitException(
                    f"Couldn't not find upstream branch {upstream_ref!r} and tag {git_ref!r}."
                )
        commits = self.get_commits_in_range(
            revision_range=f"{git_ref}..{self.lp.ref}",
            no_merge_commits=no_merge_commits,
        )
        if add_upstream_head_commit:
            commits.insert(0, self.lp.git_repo.commit(upstream_ref))

        logger.debug(f"Delta ({upstream_ref}..{self.lp.ref}): {len(commits)}")
        return commits

    def get_commits_in_range(
        self, revision_range: str, no_merge_commits: bool = True
    ) -> list[git.Commit]:
        """
        provide a list of git.Commit objects in a given git range

        :param revision_range: e.g. `branch..HEAD`, see `man git-log` for more info
        :param no_merge_commits: don't include merge commits in the list
        :return: list of commits (last commit on the current branch)
        """
        return list(
            self.lp.git_repo.iter_commits(
                rev=revision_range,
                reverse=True,
                no_merges=no_merge_commits,  # do not include merge commits in the list
            )
        )
