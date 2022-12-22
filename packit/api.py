# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
This is the official python interface for packit.
"""

import asyncio
import logging
import re
import tempfile
from datetime import datetime
from distutils.dir_util import copy_tree
from pathlib import Path
from typing import (
    Sequence,
    Callable,
    List,
    Literal,
    Tuple,
    Dict,
    Iterable,
    Optional,
    Union,
    overload,
)

import click
import git
from git.exc import GitCommandError
from ogr.abstract import PullRequest
from packaging import version as version_imported
from pkg_resources import get_distribution, DistributionNotFound
from tabulate import tabulate

from packit.actions import ActionName
from packit.config import Config
from packit.config.common_package_config import MultiplePackages
from packit.config.package_config import find_packit_yaml, load_packit_yaml
from packit.config.package_config_validator import PackageConfigValidator
from packit.constants import (
    SYNCING_NOTE,
    DISTRO_DIR,
    FROM_DIST_GIT_TOKEN,
    FROM_SOURCE_GIT_TOKEN,
    REPO_NOT_PRISTINE_HINT,
)
from packit.copr_helper import CoprHelper
from packit.distgit import DistGit
from packit.exceptions import (
    PackitCommandFailedError,
    PackitException,
    PackitFailedToCreateRPMException,
    PackitSRPMException,
    PackitSRPMNotFoundException,
    PackitRPMException,
    PackitRPMNotFoundException,
    PackitCoprException,
)
from packit.local_project import LocalProject
from packit.patches import PatchGenerator
from packit.source_git import SourceGitGenerator
from packit.status import Status
from packit.sync import sync_files, SyncFilesItem
from packit.upstream import Upstream
from packit.utils import commands
from packit.utils.bodhi import get_bodhi_client
from packit.utils.changelog_helper import ChangelogHelper
from packit.utils.extensions import assert_existence
from packit.utils.repo import (
    shorten_commit_hash,
    get_next_commit,
    commit_exists,
    get_commit_diff,
    get_commit_hunks,
    is_the_repo_pristine,
)
from packit.vm_image_build import ImageBuilder

logger = logging.getLogger(__name__)


def get_packit_version() -> str:
    try:
        return get_distribution("packitos").version
    except DistributionNotFound:
        return "NOT_INSTALLED"


class SynchronizationStatus:
    """Represents the synchronization status of source-git and dist-git

    Attributes:
        source_git_range_start: Start of commit range that is extra in
            source-git (must be synced to dist-git). None if dist-git
            is up to date.
        dist_git_range_start: Start of commit range that is extra in
            dist-git (must be synced to source-git). None if source-git
            is up to date.
    """

    def __init__(
        self, source_git_range_start: Optional[str], dist_git_range_start: Optional[str]
    ):
        self.source_git_range_start = source_git_range_start
        self.dist_git_range_start = dist_git_range_start

    def __eq__(self, other: object):
        if not isinstance(other, SynchronizationStatus):
            raise NotImplementedError
        return (
            self.source_git_range_start == other.source_git_range_start
            and self.dist_git_range_start == other.dist_git_range_start
        )


class PackitAPI:
    def __init__(
        self,
        config: Config,
        package_config: Optional[
            MultiplePackages
        ],  # validate doesn't want PackageConfig
        upstream_local_project: LocalProject = None,
        downstream_local_project: LocalProject = None,
        stage: bool = False,
        dist_git_clone_path: Optional[str] = None,
    ) -> None:
        self.config = config
        self.package_config: MultiplePackages = package_config
        self.upstream_local_project = upstream_local_project
        self.downstream_local_project = downstream_local_project
        self.stage = stage
        self._dist_git_clone_path: Optional[str] = dist_git_clone_path

        self._up: Optional[Upstream] = None
        self._dg: Optional[DistGit] = None
        self._copr_helper: Optional[CoprHelper] = None
        self._kerberos_initialized = False

    def __repr__(self):
        return (
            "PackitAPI("
            f"config='{self.config}', "
            f"package_config='{self.package_config}', "
            f"upstream_local_project='{self.upstream_local_project}', "
            f"downstream_local_project='{self.downstream_local_project}', "
            f"up='{self.up}', "
            f"dg='{self.dg}', "
            f"copr_helper='{self.copr_helper}', "
            f"stage='{self.stage}')"
        )

    @property
    def up(self) -> Upstream:
        if self._up is None:
            self._up = Upstream(
                config=self.config,
                package_config=self.package_config,
                local_project=self.upstream_local_project,
            )
        return self._up

    @property
    def dg(self) -> DistGit:
        if self._dg is None:
            self.init_kerberos_ticket()
            if not self.package_config.downstream_package_name and (
                self.downstream_local_project
                and self.downstream_local_project.working_dir
            ):
                # the path to dist-git was passed but downstream_package_name is not set
                # we know that package names are equal to repo names
                self.package_config.downstream_package_name = (
                    self.downstream_local_project.working_dir.name
                )
                logger.info(
                    "Package name was not set, we've got it from dist-git's "
                    f"directory name: {self.package_config.downstream_package_name}"
                )
            self._dg = DistGit(
                config=self.config,
                package_config=self.package_config,
                local_project=self.downstream_local_project,
                clone_path=self._dist_git_clone_path,
            )
        return self._dg

    @property
    def copr_helper(self) -> CoprHelper:
        if self._copr_helper is None:
            self._copr_helper = CoprHelper(
                upstream_local_project=self.upstream_local_project
            )
        return self._copr_helper

    def update_dist_git(
        self,
        version: Optional[str],
        upstream_ref: Optional[str],
        add_new_sources: bool,
        force_new_sources: bool,
        upstream_tag: Optional[str],
        commit_title: str,
        commit_msg: str,
        sync_default_files: bool = True,
        pkg_tool: str = "",
        mark_commit_origin: bool = False,
        check_sync_status: bool = False,
        check_dist_git_pristine: bool = True,
    ):
        """Update a dist-git repo from an upstream (aka source-git) repo

        - copy files to be synced to dist-git
        - generate and update patch files and the spec-file
        - upload source archives to the lookaside cache
        - commit the changes to dist-git, if a commit title is defined

        Args:
            version: Upstream version to update in Fedora.
            upstream_ref: For a source-git repo, use this ref as the latest upstream commit.
            add_new_sources: Download and upload source archives.
            force_new_sources: Download/upload the archive even if it's name
                is already in the cache or in sources file.
            upstream_tag: Use the message of the commit referenced by this tag to update the
                changelog in the spec-file, if requested.
            commit_title: Commit message title (aka subject-line) in dist-git.
                Do not commit if this is false-ish.
            commit_msg: Use this commit message in dist-git.
            sync_default_files: Whether to sync the default files, that is: packit.yaml and
                the spec-file.
            pkg_tool: What tool (fedpkg/centpkg) to use upload to lookaside cache.
            mark_commit_origin: Whether to include a Git-trailer in the dist-git
                commit message to mark the hash of the upstream (source-git) commit.
            check_sync_status: Check the synchronization status of the source-git
                and dist-git repos prior to performing the update.
            check_dist_git_pristine: Check whether the dist-git is pristine.
        """
        if check_sync_status:
            status = self.sync_status()
            # There are dist-git changes that need to be synced back to source-git first
            # before accepting content to be transformed from source-git to dist-git.
            if status.dist_git_range_start:
                raise PackitException(self.sync_status_string(status))
            # Both repos are already in sync.
            if not status.source_git_range_start:
                logger.info(self.sync_status_string(status))
                return

        if check_dist_git_pristine and not is_the_repo_pristine(
            self.dg.local_project.git_repo
        ):
            raise PackitException(
                "Cannot update the dist-git repo "
                f"{self.dg.local_project.git_repo.working_dir!r}, since it is not pristine."
                f"{REPO_NOT_PRISTINE_HINT}"
            )

        if sync_default_files:
            synced_files = self.package_config.get_all_files_to_sync()
        else:
            synced_files = self.package_config.files_to_sync
        # Make all paths absolute and check that they are within
        # the working directories of the repositories.
        for item in synced_files:
            item.resolve(
                src_base=self.up.local_project.working_dir,
                dest_base=self.dg.local_project.working_dir,
            )

        if self.up.with_action(action=ActionName.prepare_files):
            synced_files = self._prepare_files_to_sync(
                synced_files=synced_files,
                full_version=version,
                upstream_tag=upstream_tag,
            )

        sync_files(synced_files)

        if upstream_ref and self.up.with_action(action=ActionName.create_patches):
            patches = self.up.create_patches(
                upstream=upstream_ref,
                destination=str(self.dg.absolute_specfile_dir),
            )
            # Undo identical patches, but don't remove them
            # from the list, so that they are added to the spec-file.
            PatchGenerator.undo_identical(patches, self.dg.local_project.git_repo)
            self.dg.specfile_add_patches(
                patches, self.package_config.patch_generation_patch_id_digits
            )

        if add_new_sources or force_new_sources:
            self._handle_sources(
                force_new_sources=force_new_sources,
                pkg_tool=pkg_tool,
            )

        if commit_title:
            trailers = (
                [
                    (
                        FROM_SOURCE_GIT_TOKEN,
                        self.up.local_project.git_repo.head.commit.hexsha,
                    )
                ]
                if mark_commit_origin
                else None
            )
            self.dg.commit(
                title=commit_title,
                msg=commit_msg,
                prefix="",
                trailers=trailers,
            )

    @staticmethod
    def _transform_patch_to_source_git(patch: str, diffs: List[git.Diff]) -> str:
        """Transforms a dist-git patch to source-git.

        It's necessary to insert .distro directory to paths in the patch.
        """
        for diff in diffs:
            if diff.a_path:
                patch = patch.replace(
                    f"a/{diff.a_path}", f"a/{DISTRO_DIR}/{diff.a_path}"
                )
            if diff.b_path:
                patch = patch.replace(
                    f"b/{diff.b_path}", f"b/{DISTRO_DIR}/{diff.b_path}"
                )
        return patch

    def update_source_git(
        self, revision_range: Optional[str] = None, check_sync_status: bool = True
    ):
        """Update a source-git repo from a dist-git repo.

        Synchronizes the spec file and commits in the given revision range.
        The sources and patches in dist-git must not have been touched.

        Args:
            revision_range: Range (in git-log-like format) of commits from
                dist-git to convert to source-git. If not specified, dist-git
                commits with no counterpart in source-git will be synchronized.
            check_sync_status: Check the synchronization status of the
                source-git and dist-git repos prior to performing the update.

        Raises:
            PackitException: If the given update cannot be performed, i.e.
                sources or patches were touched.
        """
        if not revision_range and not check_sync_status:
            raise PackitException(
                "revision_range has to be specified if check_sync_status is False"
            )

        if check_sync_status:
            status = self.sync_status()
            # There are extra source-git commits
            if status.source_git_range_start:
                raise PackitException(self.sync_status_string(status))
            # There's nothing to sync
            if not status.dist_git_range_start:
                logger.info(self.sync_status_string(status))
                return
            if not revision_range:
                revision_range = f"{status.dist_git_range_start}~.."
                logger.debug(
                    f"revision_range not specified, setting to {revision_range}"
                )

        if not is_the_repo_pristine(self.up.local_project.git_repo):
            raise PackitException(
                "Cannot update the source-git repo "
                f"{self.up.local_project.git_repo.working_dir!r}, since it is not pristine."
                f"{REPO_NOT_PRISTINE_HINT}"
            )

        dg_release = self.dg.specfile.expanded_release
        up_release = self.up.specfile.expanded_release
        if dg_release != up_release:
            logger.info(
                f"Release differs between dist-git and source-git ("
                f"{dg_release} in dist-git and {up_release} in source-git). "
                f"Trying to continue with the update."
            )

        # Do the checks beforehand but store commits and diffs to avoid recomputing.
        # Getting patch of a git commit is costly as per GitPython docs.
        commits: List[git.Commit] = []
        diffs: List[List[git.Diff]] = []
        patch_suffix = ".patch"
        distro_path = self.up.local_project.working_dir / DISTRO_DIR
        for commit in self.dg.local_project.git_repo.iter_commits(
            revision_range, reverse=True
        ):
            commits.append(commit)
            diffs.append(get_commit_diff(commit))
            for diff in diffs[-1]:
                if diff.a_path == "sources" or diff.b_path == "sources":
                    raise PackitException(
                        f"The sources file was modified in commit "
                        f"{commit.hexsha} which is part of the provided range. "
                        f"Such operation is not supported."
                    )
                a_path = diff.a_path or ""
                b_path = diff.b_path or ""
                # FIXME: this check is not great, but if we want to be more precise, we would
                #   have to parse the spec in each checkout of dist-git
                if a_path.endswith(patch_suffix) or b_path.endswith(patch_suffix):
                    raise PackitException(
                        f"A patch was modified in commit {commit.hexsha} "
                        f"which is not supported by this command."
                    )

        logger.info(f"Synchronizing {len(commits)} commits.")
        for i, commit in enumerate(commits):
            logger.info(f"Applying commit {commit}.")
            # GitPython does not store the raw diff of the patch in its representation.
            # We can delete and rename based on the information from GitPython but additions
            # and modifications require git-apply on a patch. We need to manually parse
            # the corresponding patch hunk.
            hunks = get_commit_hunks(self.dg.local_project.git_repo, commit)
            for j, diff in enumerate(diffs[i]):
                if diff.deleted_file:
                    path = distro_path / diff.a_path
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass  # missing_ok argument to unlink was added in 3.8 which is not in EPEL
                elif diff.renamed_file:
                    path = distro_path / diff.a_path
                    try:
                        path.rename(distro_path / Path(diff.b_path).name)
                    except FileNotFoundError as e:
                        raise PackitException(
                            f"File {diff.a_path} to be renamed does not exist in source-git."
                        ) from e
                else:
                    # The order of `hunks` should match the order of `diffs`, they are using the
                    # same git commands.
                    with tempfile.TemporaryDirectory() as tmp:
                        patch = self._transform_patch_to_source_git(hunks[j], diffs[i])
                        changes_path = Path(tmp) / "changes.patch"
                        changes_path.write_text(f"{patch}\n")
                        try:
                            self.up.local_project.git_repo.git.apply(changes_path)
                        except GitCommandError as e:
                            # Gitignore is reset when creating source-git, git-apply may fail
                            if diff.b_path == ".gitignore":
                                logger.info(
                                    f"Commit {commit} contains an inapplicable .gitignore "
                                    f"change, skipping this part of the commit."
                                )
                                continue
                            raise PackitException(
                                f"Commit {commit} could not be applied to source-git."
                            ) from e

            title, _, message = commit.message.partition("\n")
            message = message.strip()
            if (
                self.up.local_project.git_repo.is_dirty()
                or self.up.local_project.git_repo.untracked_files
            ):
                self.up.commit(
                    title=title,
                    msg=message,
                    prefix="",
                    trailers=[(FROM_DIST_GIT_TOKEN, commit.hexsha)],
                )
            else:
                logger.info(
                    f"Commit {commit} had no changes to be applied, skipping it."
                )

    def _get_latest_commit_update_pair(self) -> Tuple[str, str]:
        """Finds the latest pair of commits which was created by updating
        source-git from dist-git (or vice versa) denoted by git trailers.

        Determining the latest pair by commit time is not sufficient since
        the datetime may be the same in all commits. We need to check for
        actual parent-child relationships to determine the ordering.

        Returns:
            A tuple containing hash of the source-git commit and hash of the
                corresponding dist-git commit. This represents the latest
                update pair in both source-git and dist-git.

        Raises:
            PackitException, if no commits with git trailers that are used
                for checking the sync could be found in either of the
                repositories.
        """
        # Use source-git commit first in both tuples for consistency
        sg_update_commits = [
            (
                c.hexsha,
                re.search(
                    rf"^{re.escape(FROM_DIST_GIT_TOKEN)}: (.+)$",
                    c.message,
                    re.MULTILINE,
                ).group(1),
            )
            for c in self.up.local_project.git_repo.iter_commits(
                max_count=1, grep=rf"^{re.escape(FROM_DIST_GIT_TOKEN)}: .\+$"
            )
        ]
        dg_update_commits = [
            (
                re.search(
                    rf"^{re.escape(FROM_SOURCE_GIT_TOKEN)}: (.+)$",
                    c.message,
                    re.MULTILINE,
                ).group(1),
                c.hexsha,
            )
            for c in self.dg.local_project.git_repo.iter_commits(
                max_count=1, grep=rf"^{re.escape(FROM_SOURCE_GIT_TOKEN)}: .\+$"
            )
        ]
        if sg_update_commits and not commit_exists(
            self.dg.local_project.git_repo, sg_update_commits[0][1]
        ):
            raise PackitException(
                f"Commit '{sg_update_commits[0][1]}' referenced in {FROM_DIST_GIT_TOKEN} "
                f"git trailer does not exist in dist-git."
            )
        if dg_update_commits and not commit_exists(
            self.up.local_project.git_repo, dg_update_commits[0][0]
        ):
            raise PackitException(
                f"Commit '{dg_update_commits[0][0]}' referenced in {FROM_SOURCE_GIT_TOKEN} "
                f"git trailer does not exist in source-git."
            )
        if sg_update_commits and dg_update_commits:
            # Check ancestor relationships, the situation is as follows:
            #     source-git HEAD          dist-git HEAD
            #           |                       |
            # sg_update_commits[0][0] <- sg_update_commits[0][1]
            #           |                       |
            # dg_update_commits[0][0] -> dg_update_commits[0][1]

            # sg_update_commits and dg_update_commits could be swapped,
            # we need to determine the correct order using
            #   git merge-base --is-ancestor
            # Ancestor is the older commit, we want to return the newer
            if self.up.local_project.git_repo.is_ancestor(
                sg_update_commits[0][0], dg_update_commits[0][0]
            ):
                return dg_update_commits[0]
            else:
                return sg_update_commits[0]
        elif sg_update_commits:
            return sg_update_commits[0]
        elif dg_update_commits:
            return dg_update_commits[0]
        else:
            raise PackitException(
                "No git commits with trailers to mark synchronization points were found."
            )

    def sync_status(self) -> SynchronizationStatus:
        """Checks the sync status of source-git and dist-git.

        Returns:
            A dataclass representing the synchronization status of
            source-git and dist-git containing the range of commits
            that need to be synchronized.

        Raises:
            PackitException, if no commits with git trailers that are used
                for checking the sync could be found in either of the
                repositories.
        """
        sg_sync_point, dg_sync_point = self._get_latest_commit_update_pair()
        return SynchronizationStatus(
            source_git_range_start=get_next_commit(
                self.up.local_project.git_repo, sg_sync_point
            ),
            dist_git_range_start=get_next_commit(
                self.dg.local_project.git_repo, dg_sync_point
            ),
        )

    def sync_status_string(
        self,
        status: SynchronizationStatus = None,
        source_git: Union[Path, str, None] = None,
        dist_git: Union[Path, str, None] = None,
    ) -> str:
        """Returns the synchronization status of source-git and dist-git as a string.

        Args:
            status: Synchronization status of source-git and dist-git.
            source_git: Path to source-git as specified by the user.
            dist_git: Path to dist-git as specified by the user.
        """
        status = status or self.sync_status()
        source_git = source_git or self.up.local_project.working_dir
        dist_git = dist_git or self.dg.local_project.working_dir

        if status.source_git_range_start and status.dist_git_range_start:
            return f"""'{source_git}' and '{dist_git}' have diverged.
Sync status needs to be reestablished manually.
The first source-git commit to be synced is '{shorten_commit_hash(status.source_git_range_start)}'.
The first dist-git commit to be synced is '{shorten_commit_hash(status.dist_git_range_start)}'.
"""
        elif status.source_git_range_start:
            number_of_commits = len(
                list(
                    self.up.local_project.git_repo.iter_commits(
                        f"{status.source_git_range_start}~..", ancestry_path=True
                    )
                )
            )
            return f"""'{source_git}' is ahead of '{dist_git}' by {number_of_commits} commits.
Use "packit source-git update-dist-git {source_git} {dist_git}"
to transform changes from '{source_git}' to '{dist_git}'.
The first source-git commit to be synced is '{shorten_commit_hash(status.source_git_range_start)}'.
"""
        elif status.dist_git_range_start:
            number_of_commits = len(
                list(
                    self.dg.local_project.git_repo.iter_commits(
                        f"{status.dist_git_range_start}~..", ancestry_path=True
                    )
                )
            )
            short_hash = shorten_commit_hash(status.dist_git_range_start)
            return f"""'{source_git}' is behind of '{dist_git}' by {number_of_commits} commits.
Use "packit source-git update-source-git {dist_git} {source_git}
{short_hash}~..\" to transform changes from '{dist_git}' to '{source_git}'.
The first dist-git commit to be synced is '{short_hash}'.
"""
        else:
            return f"'{source_git}' is up to date with '{dist_git}'."

    @overload
    def sync_release(
        self,
        dist_git_branch: Optional[str] = None,
        version: Optional[str] = None,
        tag: Optional[str] = None,
        use_local_content=False,
        add_new_sources=True,
        force_new_sources=False,
        upstream_ref: Optional[str] = None,
        create_pr: Literal[True] = True,
        force: bool = False,
        create_sync_note: bool = True,
        title: Optional[str] = None,
        description: Optional[str] = None,
        sync_default_files: bool = True,
        local_pr_branch_suffix: str = "update",
        mark_commit_origin: bool = False,
        use_downstream_specfile: bool = False,
    ) -> PullRequest:
        """Overload for type-checking; return PullRequest if create_pr=True."""

    @overload
    def sync_release(
        self,
        dist_git_branch: Optional[str] = None,
        version: Optional[str] = None,
        tag: Optional[str] = None,
        use_local_content=False,
        add_new_sources=True,
        force_new_sources=False,
        upstream_ref: Optional[str] = None,
        create_pr: Literal[False] = False,
        force: bool = False,
        create_sync_note: bool = True,
        title: Optional[str] = None,
        description: Optional[str] = None,
        sync_default_files: bool = True,
        local_pr_branch_suffix: str = "update",
        mark_commit_origin: bool = False,
        use_downstream_specfile: bool = False,
    ) -> None:
        """Overload for type-checking; return None if create_pr=False."""

    def sync_release(
        self,
        dist_git_branch: Optional[str] = None,
        version: Optional[str] = None,
        tag: Optional[str] = None,
        use_local_content=False,
        add_new_sources=True,
        force_new_sources=False,
        upstream_ref: Optional[str] = None,
        create_pr: bool = True,
        force: bool = False,
        create_sync_note: bool = True,
        title: Optional[str] = None,
        description: Optional[str] = None,
        sync_default_files: bool = True,
        local_pr_branch_suffix: str = "update",
        mark_commit_origin: bool = False,
        use_downstream_specfile: bool = False,
    ) -> Optional[PullRequest]:
        """
        Update given package in dist-git

        Args:
            dist_git_branch: Branch in dist-git, defaults to repo's default branch.
            use_local_content: Don't check out anything.
            version: Upstream version to update in dist-git.
            tag: Upstream git tag.
            add_new_sources: Download and upload source archives.
            force_new_sources: Download/upload the archive even if it's
                name is already in the cache or in sources file.
            upstream_ref: For a source-git repo, use this ref as the latest upstream commit.
            create_pr: Create a pull request if set to True.
            force: Ignore changes in the git index.
            create_sync_note: Whether to create a note about the sync in the dist-git repo.
            title: Title (first line) of the commit & PR.
            description: Description of the commit & PR.
            sync_default_files: Whether to sync the default files, that is:
                packit.yaml and the spec-file.
            local_pr_branch_suffix: When create_pr is True, we push into a newly created
                branch and create a PR from it. This param specifies a suffix attached
                to the created branch name, so that we can have more PRs for the same
                dg branch at one time.
            mark_commit_origin: Whether to include a Git-trailer in the dist-git
                commit message to mark the hash of the upstream (source-git) commit.
            use_downstream_specfile: Use the downstream specfile instead
                of getting the upstream one (used by packit-service in pull_from_upstream)

        Returns:
            The created (or existing if one already exists) PullRequest if
            create_pr is True, else None.

        Raises:
            PackitException, if both 'version' and 'tag' are provided.
            PackitException, if the version of the latest upstream release cannot be told.
            PackitException, if the upstream repo or dist-git is dirty.
        """
        dist_git_branch = (
            dist_git_branch or self.dg.local_project.git_project.default_branch
        )
        # process version and tag parameters
        if version and tag:
            raise PackitException(
                "Function parameters version and tag are mutually exclusive."
            )
        elif not tag:
            version = version or self.up.get_latest_released_version()
            if not version:
                raise PackitException(
                    "Could not figure out version of latest upstream release. "
                    "You can specify it as an argument."
                )
            upstream_tag = self.up.convert_version_to_tag(version)
        else:
            upstream_tag = tag
            version = self.up.get_version_from_tag(tag)

        assert_existence(self.up.local_project, "Upstream local project")
        assert_existence(self.dg.local_project, "Dist-git local project")
        if self.dg.is_dirty():
            raise PackitException(
                f"The distgit repository {self.dg.local_project.working_dir} is dirty."
                f"This is not supported."
            )
        if not force and self.up.is_dirty() and not use_local_content:
            raise PackitException(
                "The repository is dirty, will not discard the changes. Use --force to bypass."
            )
        # do not add anything between distgit clone and saving gpg keys!
        self.up.allowed_gpg_keys = self.dg.get_allowed_gpg_keys_from_downstream_config()

        upstream_ref = self.up._expand_git_ref(
            upstream_ref or self.package_config.upstream_ref
        )

        current_up_branch = self.up.active_branch
        try:
            # we want to check out the tag only when local_content is not set
            # and it's an actual upstream repo and not source-git
            if upstream_ref:
                logger.info(
                    "We will not check out the upstream tag "
                    "because this is a source-git repo."
                )
            elif not use_local_content:
                self.up.local_project.checkout_release(upstream_tag)
            self.up.run_action(actions=ActionName.post_upstream_clone)

            if not use_downstream_specfile:
                spec_ver = self.up.get_specfile_version()
                if version_imported.parse(version) > version_imported.parse(spec_ver):
                    logger.warning(f"Version {spec_ver!r} in spec file is outdated.")

            self.dg.check_last_commit()

            self.up.run_action(actions=ActionName.pre_sync)
            self.dg.create_branch(
                dist_git_branch,
                base=f"remotes/origin/{dist_git_branch}",
                setup_tracking=True,
            )

            # fetch and reset --hard upstream/$branch?
            logger.info(f"Using {dist_git_branch!r} dist-git branch.")
            self.dg.update_branch(dist_git_branch)
            self.dg.checkout_branch(dist_git_branch)

            if use_downstream_specfile:
                logger.info(
                    "Using the downstream specfile instead of the upstream one."
                )
                self.up.set_specfile(self.dg.specfile)

            if create_pr:
                local_pr_branch = (
                    f"{version}-{dist_git_branch}-{local_pr_branch_suffix}"
                )
                self.dg.create_branch(local_pr_branch)
                self.dg.checkout_branch(local_pr_branch)

            if create_sync_note and self.package_config.create_sync_note:
                readme_path = self.dg.local_project.working_dir / "README.packit"
                logger.debug(f"README: {readme_path}")
                readme_path.write_text(
                    SYNCING_NOTE.format(packit_version=get_packit_version())
                )

            description = description or (
                f"Upstream tag: {upstream_tag}\n"
                f"Upstream commit: {self.up.local_project.commit_hexsha}\n"
            )
            self.update_dist_git(
                version,
                upstream_ref,
                add_new_sources=add_new_sources,
                force_new_sources=force_new_sources,
                upstream_tag=upstream_tag,
                commit_title=title or f"[packit] {version} upstream release",
                commit_msg=description,
                sync_default_files=sync_default_files,
                mark_commit_origin=mark_commit_origin,
                check_dist_git_pristine=False,
            )

            pr = None
            if create_pr:
                pr = self.push_and_create_pr(
                    pr_title=title or f"Update to upstream release {version}",
                    pr_description=description,
                    git_branch=dist_git_branch,
                    repo=self.dg,
                )
            else:
                self.dg.push(refspec=f"HEAD:{dist_git_branch}")
        finally:
            if not use_local_content and not upstream_ref:
                logger.info(f"Checking out the original branch {current_up_branch}.")
                self.up.local_project.git_repo.git.checkout(current_up_branch, "-f")
            self.dg.refresh_specfile()
            self.dg.local_project.git_repo.git.reset("--hard", "HEAD")
        return pr

    def get_pr_default_title_and_description(self):
        """Create a default title and description to be used
        in a PR for updating upstream from a dist-git push.

        Returns:
            (title, description):
            The title str will be the first line in the latest commit.
            The description str will be all the other lines in the latest commit, if any.
        """
        message = self.dg.local_project.git_repo.head.commit.message
        lines = list(message.split("\n"))
        title = lines[0] or f"({self.dg.local_project.commit_hexsha})"
        description = "\n".join(lines[1:]).strip()
        return f"Update upstream to latest dist-git commit: {title}", description

    def sync_push(
        self,
        source_git_branch: Optional[str] = None,
        create_pr: bool = True,
        title: Optional[str] = None,
        description: Optional[str] = None,
        force: bool = False,
    ) -> Optional[PullRequest]:
        """
        When dist-git is updated then update the source-git repository by opening a PR.

        Args:
            source_git_branch: Branch in source-git, defaults to repo's default branch.
            create_pr: Create a pull request if set to True.
            force: Ignore changes in the git index.
            title: Title (first line) of the commit & PR.
            description: Description of the commit & PR.

        Returns:
            The created (or existing if one already exists) PullRequest if
            create_pr is True, else None.

        Raises:
            PackitException, if the upstream repo or dist-git is dirty.
        """
        assert_existence(self.up.local_project, "Upstream local project")
        assert_existence(self.dg.local_project, "Dist-git local project")

        if self.up.is_dirty():
            raise PackitException(
                f"The upstream repository {self.up.local_project.working_dir} is dirty."
                f"This is not supported."
            )
        if not force and self.dg.is_dirty():
            raise PackitException(
                f"The distgit repository {self.up.local_project.working_dir} is dirty,"
                " will not discard the changes. Use --force to bypass."
            )

        source_git_branch = (
            source_git_branch or self.up.local_project.git_project.default_branch
        )
        pr = None
        try:
            self.up.checkout_branch(source_git_branch)
            self.update_source_git()

            (
                default_title,
                default_description,
            ) = self.get_pr_default_title_and_description()
            if create_pr:
                pr = self.push_and_create_pr(
                    pr_title=title or default_title,
                    pr_description=description or default_description,
                    git_branch=source_git_branch,
                    repo=self.up,
                )
            else:
                self.up.push(refspec=f"HEAD:{source_git_branch}")
        finally:
            self.up.local_project.git_repo.git.reset("--hard", "HEAD")

        return pr

    def _prepare_files_to_sync(
        self, synced_files: List[SyncFilesItem], full_version: str, upstream_tag: str
    ) -> List[SyncFilesItem]:
        """
        Returns the list of files to sync to dist-git as is.

        With spec-file, we have two modes:
        * The `sync_changelog` option is set. => Spec-file can be synced as other files.
        * Sync the content of the spec-file (but changelog) here and exclude spec-file otherwise.

        Args:
            synced_files: A list of SyncFilesItem.
            full_version: Version to be set in the spec-file.
            upstream_tag: The commit message of this commit is going to be used
                to update the changelog in the spec-file.

        Returns:
            The list of synced files with the spec-file removed if it was updated.
        """
        if self.package_config.sync_changelog:
            return synced_files

        # add entry to changelog
        ChangelogHelper(self.up, self.dg, self.package_config).update_dist_git(
            full_version=full_version, upstream_tag=upstream_tag
        )

        # exclude spec, we have special plans for it
        return list(
            filter(
                None,
                [
                    x.drop_src(self.up.get_absolute_specfile_path())
                    for x in synced_files
                ],
            )
        )

    def sync_from_downstream(
        self,
        dist_git_branch: Optional[str] = None,
        upstream_branch: Optional[str] = None,
        no_pr: bool = False,
        fork: bool = True,
        remote_name: Optional[str] = None,
        exclude_files: Iterable[str] = None,
        force: bool = False,
        sync_only_specfile: bool = False,
    ):
        """
        Sync content of Fedora dist-git repo back to upstream

        :param dist_git_branch: branch in dist-git, defaults to repo's default branch
        :param upstream_branch: upstream branch, defaults to repo's default branch
        :param no_pr: won't create a pull request if set to True
        :param fork: forks the project if set to True
        :param remote_name: name of remote where we should push; if None, try to find a ssh_url
        :param exclude_files: files that will be excluded from the sync
        :param force: ignore changes in the git index
        :param sync_only_specfile: whether to sync only content of specfile
        """
        exclude_files = exclude_files or []
        if not dist_git_branch:
            dist_git_branch = self.dg.local_project.git_project.default_branch
            logger.info(f"Dist-git branch not set, defaulting to {dist_git_branch!r}.")
        if not upstream_branch:
            upstream_branch = self.up.local_project.git_project.default_branch
            logger.info(f"Upstream branch not set, defaulting to {upstream_branch!r}.")
        logger.info(f"Upstream active branch: {self.up.active_branch}")

        if not force and self.up.is_dirty():
            raise PackitException(
                "The repository is dirty, will not discard the changes. Use --force to bypass."
            )
        self.dg.update_branch(dist_git_branch)
        self.dg.checkout_branch(dist_git_branch)

        logger.info(f"Using {dist_git_branch!r} dist-git branch.")

        if no_pr:
            self.up.checkout_branch(upstream_branch)
        else:
            local_pr_branch = f"{dist_git_branch}-downstream-sync"
            self.up.create_branch(local_pr_branch)
            self.up.checkout_branch(local_pr_branch)

        files = (
            [self.package_config.get_specfile_sync_files_item(from_downstream=True)]
            if sync_only_specfile
            else self.package_config.files_to_sync
        )

        # Drop files to be excluded from the sync.
        for ef in exclude_files:
            files = [
                f.drop_src(ef, criteria=lambda x, y: Path(x).name == y)
                for f in files
                if f is not None
            ]
        # Make paths absolute and check if they are within the
        # working directories.
        for file in files:
            file.resolve(
                src_base=self.dg.local_project.working_dir,
                dest_base=self.up.local_project.working_dir,
            )
        sync_files(files)

        if not no_pr:
            description = f"Downstream commit: {self.dg.local_project.commit_hexsha}\n"

            commit_msg = f"Sync from downstream branch {dist_git_branch!r}"
            pr_title = f"Update from downstream branch {dist_git_branch!r}"

            self.up.commit(title=commit_msg, msg=description)

            # the branch may already be up, let's push forcefully
            source_branch, fork_username = self.up.push_to_fork(
                self.up.local_project.ref,
                fork=fork,
                force=True,
                remote_name=remote_name,
            )
            self.up.create_pull(
                pr_title,
                description,
                source_branch=source_branch,
                target_branch=upstream_branch,
                fork_username=fork_username,
            )

    def push_and_create_pr(
        self,
        pr_title: str,
        pr_description: str,
        git_branch: str,
        repo: Union[Upstream, DistGit],
    ) -> PullRequest:
        # the branch may already be up, let's push forcefully
        repo.push_to_fork(repo.local_project.ref, force=True)
        pr = repo.existing_pr(
            pr_title, pr_description.rstrip(), git_branch, repo.local_project.ref
        )
        if pr is None:
            pr = repo.create_pull(
                pr_title,
                pr_description,
                source_branch=repo.local_project.ref,
                target_branch=git_branch,
            )
        else:
            logger.debug(f"PR already exists: {pr.url}")
        return pr

    def _handle_sources(
        self,
        force_new_sources: bool,
        pkg_tool: str = "",
    ):
        """Download upstream archive and upload it to dist-git lookaside cache.

        Args:
            force_new_sources: Download/upload the archive even if it's
                name is already in the cache or in sources file.
                Actually, fedpkg/centpkg won't upload it if archive with the same
                name & hash is already there, so this might be useful only if
                you want to upload archive with the same name but different hash.
            pkg_tool: Tool to upload sources.
        """

        archives_to_upload = False
        sources_file = self.dg.local_project.working_dir / "sources"

        # Here, dist-git spec-file has already been updated from the upstream spec-file.
        # => Any update done to the Source tags in upstream
        # is already available in the dist-git spec-file.
        for upstream_archive_name in self.dg.upstream_archive_names:
            archive_name_in_cache = self.dg.is_archive_in_lookaside_cache(
                upstream_archive_name
            )
            archive_name_in_sources_file = (
                sources_file.is_file()
                and upstream_archive_name in sources_file.read_text()
            )

            if not archive_name_in_cache or not archive_name_in_sources_file:
                archives_to_upload = True
        if not archives_to_upload and not force_new_sources:
            return

        # There is at least one archive to upload,
        # because it is missing from lookaside, sources file, or both,
        # or because force_new_sources is set.
        archives = self.dg.download_upstream_archives()
        self.init_kerberos_ticket()
        # Upload all of archives. If we uploaded only those that need uploading,
        # we would lose the unchanged ones from sources file,
        # because upload_to_lookaside_cache maintains the sources file in addition
        # to uploading, and it replaces it entirely, losing the previous content
        self.dg.upload_to_lookaside_cache(archives=archives, pkg_tool=pkg_tool)

    def build(
        self,
        dist_git_branch: str,
        scratch: bool = False,
        nowait: bool = False,
        koji_target: Optional[str] = None,
        from_upstream: bool = False,
        release_suffix: Optional[str] = None,
        srpm_path: Optional[Path] = None,
    ):
        """
        Build component in Fedora infra (defaults to koji).

        Args:
            dist_git_branch: Branch in dist-git.
            scratch: Defines whether the build should be scratch build.
            nowait: Defines whether packit should wait for the build to finish
                or not.
            koji_target: Koji target to build for, see `koji list-targets`.
            from_upstream: Specifies whether the build should be done directly
                from the upstream checkout.
            release_suffix: Specifies release suffix to be used for SRPM build.
            srpm_path: Specifies the path to the SRPM. If given, it is used for
                the Koji build instead of the dist-git sources or upstream (if
                `from_upstream` is set).
        """
        logger.info(f"Using {dist_git_branch!r} dist-git branch")
        self.init_kerberos_ticket()

        if from_upstream and not srpm_path:
            srpm_path = self.create_srpm(
                srpm_dir=self.up.local_project.working_dir,
                release_suffix=release_suffix,
            )
        if srpm_path:
            return self.up.koji_build(
                scratch=scratch,
                nowait=nowait,
                koji_target=koji_target,
                srpm_path=srpm_path,
            )

        self.dg.create_branch(
            dist_git_branch,
            base=f"remotes/origin/{dist_git_branch}",
            setup_tracking=True,
        )

        self.dg.update_branch(dist_git_branch)
        self.dg.checkout_branch(dist_git_branch)

        self.dg.build(scratch=scratch, nowait=nowait, koji_target=koji_target)

    def create_update(
        self,
        dist_git_branch: str,
        update_type: str,
        update_notes: Optional[str] = None,
        koji_builds: Sequence[str] = None,
        bugzilla_ids: Optional[List[int]] = None,
    ):
        """
        Create bodhi update.

        Args:
            dist_git_branch: Git reference.
            update_type: Type of the update, check CLI.
            update_notes: Notes about the update to be displayed in Bodhi. If not specified,
              automatic update notes including a changelog diff since the latest stable build
              will be generated.
            koji_builds: List of Koji builds or `None` (picks latest).
            bugzilla_ids: List of Bugzillas that are resolved with the update.
        """
        logger.debug(
            f"Create bodhi update, "
            f"builds={koji_builds}, dg_branch={dist_git_branch}, type={update_type}"
        )
        self.dg.create_bodhi_update(
            koji_builds=koji_builds,
            dist_git_branch=dist_git_branch,
            update_notes=update_notes,
            update_type=update_type,
            bugzilla_ids=bugzilla_ids,
        )

    def prepare_sources(
        self,
        upstream_ref: Optional[str] = None,
        bump_version: bool = True,
        release_suffix: Optional[str] = None,
        result_dir: Union[Path, str] = None,
        create_symlinks: Optional[bool] = True,
    ) -> None:
        """
        Prepare sources for an SRPM build.

        Args:
            upstream_ref: git ref to upstream commit used in source-git
            release_suffix: specifies local release suffix. `None` represents default suffix.
            bump_version: specifies whether version should be changed in the spec-file.
            result_dir: directory where the specfile directory content should be copied
            create_symlinks: whether symlinks should be created instead of copying the files
                (currently when the archive is created outside the specfile dir, or in the future
                 if we will create symlinks in some other places)
        """
        self.up.run_action(actions=ActionName.post_upstream_clone)

        try:
            self.up.prepare_upstream_for_srpm_creation(
                upstream_ref=upstream_ref,
                bump_version=bump_version,
                release_suffix=release_suffix,
                create_symlinks=create_symlinks,
            )
        except Exception as ex:
            raise PackitSRPMException(
                f"Preparation of the repository for creation of an SRPM failed: {ex}"
            ) from ex

        if result_dir:
            self.copy_sources(result_dir)

        logger.info(
            f"Directory with sources: {result_dir or self.up.absolute_specfile_dir}"
        )

    def copy_sources(self, result_dir) -> None:
        """
        Copy content of the specfile directory to the `result_dir`.

        Args:
            result_dir: directory where the specfile directory content should be copied
        """
        logger.debug(f"Copying {self.up.absolute_specfile_dir} -> {result_dir}")
        copy_tree(
            str(self.up.absolute_specfile_dir), str(result_dir), preserve_symlinks=True
        )

    def create_srpm(
        self,
        output_file: Optional[str] = None,
        upstream_ref: Optional[str] = None,
        srpm_dir: Union[Path, str] = None,
        bump_version: bool = True,
        release_suffix: Optional[str] = None,
    ) -> Path:
        """
        Create srpm from the upstream repo

        Args:
            upstream_ref: git ref to upstream commit
            output_file: path + filename where the srpm should be written, defaults to cwd
            srpm_dir: path to the directory where the srpm is meant to be placed
            release_suffix: specifies local release suffix. `None` represents default suffix.
            bump_version: specifies whether version should be changed in the spec-file.

        Returns:
            a path to the srpm
        """
        try:
            self.prepare_sources(upstream_ref, bump_version, release_suffix)
            try:
                srpm_path = self.up.create_srpm(
                    srpm_path=output_file, srpm_dir=srpm_dir
                )
            except PackitSRPMException:
                raise
            except Exception as ex:
                raise PackitSRPMException(
                    f"An unexpected error occurred when creating the SRPM: {ex}"
                ) from ex

            if not srpm_path.exists():
                raise PackitSRPMNotFoundException(
                    f"SRPM was created successfully, but can't be found at {srpm_path}"
                )
            return srpm_path
        finally:
            self.clean()

    def create_rpms(
        self,
        upstream_ref: Optional[str] = None,
        rpm_dir: str = None,
        release_suffix: Optional[str] = None,
    ) -> List[Path]:
        """
        Create RPMs from the upstream repository.

        Args:
            upstream_ref: Git reference to the upstream commit.
            rpm_dir: Path to the directory where the RPMs are meant to be placed.
            release_suffix: Release suffix that is used during modification of specfile.

        Returns:
            List of paths to the built RPMs.
        """
        self.up.run_action(actions=ActionName.post_upstream_clone)

        try:
            self.up.prepare_upstream_for_srpm_creation(
                upstream_ref=upstream_ref, release_suffix=release_suffix
            )
        except Exception as ex:
            raise PackitRPMException(
                f"Preparing of the upstream to the RPM build failed: {ex}"
            ) from ex

        try:
            rpm_paths = self.up.create_rpms(rpm_dir=rpm_dir)
        except PackitRPMException:
            raise
        except Exception as ex:
            raise PackitRPMException(
                f"An unexpected error occurred when creating the RPMs: {ex}"
            ) from ex

        for rpm_path in rpm_paths:
            if not rpm_path.exists():
                raise PackitRPMNotFoundException(
                    f"RPM was created successfully, but can't be found at {rpm_path}"
                )
        return rpm_paths

    @staticmethod
    async def status_get_downstream_prs(status) -> List[Tuple[int, str, str]]:
        try:
            await asyncio.sleep(0)
            return status.get_downstream_prs()
        except Exception as exc:
            # https://github.com/packit/ogr/issues/67 work-around
            logger.debug(f"Failed when getting downstream PRs: {exc}")
            return []

    @staticmethod
    async def status_get_dg_versions(status) -> Dict:
        try:
            await asyncio.sleep(0)
            return status.get_dg_versions()
        except Exception as exc:
            logger.debug(f"Failed when getting Dist-git versions: {exc}")
            return {}

    @staticmethod
    async def status_get_up_releases(status) -> List:
        try:
            await asyncio.sleep(0)
            return status.get_up_releases()
        except Exception as exc:
            logger.debug(f"Failed when getting upstream releases: {exc}")
            return []

    @staticmethod
    async def status_get_koji_builds(status) -> Dict:
        try:
            await asyncio.sleep(0)
            return status.get_koji_builds()
        except Exception as exc:
            logger.debug(f"Failed when getting Koji builds: {exc}")
            return {}

    @staticmethod
    async def status_get_copr_builds(status) -> List:
        try:
            await asyncio.sleep(0)
            return status.get_copr_builds()
        except Exception as exc:
            logger.debug(f"Failed when getting Copr builds: {exc}")
            return []

    @staticmethod
    async def status_get_updates(status) -> List:
        try:
            await asyncio.sleep(0)
            return status.get_updates()
        except Exception as exc:
            logger.debug(f"Failed when getting Bodhi updates: {exc}")
            return []

    @staticmethod
    async def status_main(status: Status) -> List:
        """
        Schedule repository data retrieval calls concurrently.
        :param status: status of the package
        :return: awaitable tasks
        """
        res = await asyncio.gather(
            PackitAPI.status_get_downstream_prs(status),
            PackitAPI.status_get_dg_versions(status),
            PackitAPI.status_get_up_releases(status),
            PackitAPI.status_get_koji_builds(status),
            PackitAPI.status_get_copr_builds(status),
            PackitAPI.status_get_updates(status),
        )
        return res

    def status(self) -> None:
        status = Status(self.config, self.package_config, self.up, self.dg)
        (
            ds_prs,
            dg_versions,
            up_releases,
            koji_builds,
            copr_builds,
            updates,
        ) = asyncio.run(self.status_main(status))

        if ds_prs:
            click.echo("\nDownstream PRs:")
            click.echo(tabulate(ds_prs, headers=["ID", "Title", "URL"]))
        else:
            click.echo("\nNo downstream PRs found.")

        if dg_versions:
            click.echo("\nDist-git versions:")
            for branch, dg_version in dg_versions.items():
                click.echo(f"{branch: <10} {dg_version}")
        else:
            click.echo("\nNo Dist-git versions found.")

        if up_releases:
            click.echo("\nUpstream releases:")
            upstream_releases_str = "\n".join(
                f"{release.tag_name}" for release in up_releases
            )
            click.echo(upstream_releases_str)
        else:
            click.echo("\nNo upstream releases found.")

        if updates:
            click.echo("\nLatest Bodhi updates:")
            click.echo(tabulate(updates, headers=["Update", "Karma", "status"]))
        else:
            click.echo("\nNo Bodhi updates found.")

        if koji_builds:
            click.echo("\nLatest Koji builds:")
            for branch, branch_builds in koji_builds.items():
                click.echo(f"{branch: <8} {branch_builds}")
        else:
            click.echo("\nNo Koji builds found.")

        if copr_builds:
            click.echo("\nLatest Copr builds:")
            click.echo(
                tabulate(copr_builds, headers=["Build ID", "Project name", "Status"])
            )
        else:
            click.echo("\nNo Copr builds found.")

    def run_copr_build(
        self,
        project: str,
        chroots: List[str],
        owner: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        upstream_ref: Optional[str] = None,
        list_on_homepage: bool = False,
        preserve_project: bool = False,
        additional_packages: Optional[List[str]] = None,
        additional_repos: Optional[List[str]] = None,
        request_admin_if_needed: bool = False,
        enable_net: bool = True,
        release_suffix: Optional[str] = None,
        srpm_path: Optional[Path] = None,
    ) -> Tuple[int, str]:
        """
        Submit a build to copr build system using an SRPM using the current checkout.

        Args:
            project: Name of the copr project to build inside

                Defaults to something long and ugly.
            chroots: List of Copr chroots (targets), e.g. `fedora-rawhide-x86_64`.
            owner: Defaults to username from copr config file.
            description: Description of the Copr project.
            instructions: Installation instructions for the Copr project.
            upstream_ref: Git ref to upstream commit.
            list_on_homepage: Specifies whether created Copr project will be
                visible on Copr's homepage.
            preserve_project: Specifies whether created Copr project should be
                automatically deleted after specific period.
            additional_packages: Buildroot packages for the chroot [DOES NOT WORK YET].
            additional_repos: Buildroot additional additional_repos.
            request_admin_if_needed: Specifies whether to ask for admin privileges,
                if changes to configuration of Copr project are required.
            enable_net: Specifies whether created Copr build should have access
                to network during its build.
            release_suffix: Release suffix that is used during generation of SRPM.
            srpm_path: Specifies the path to the prebuilt SRPM. It is preferred
                to the implicit creation of the SRPM.

        Returns:
            ID of the created build and URL to the build web page.
        """
        if not srpm_path:
            srpm_path = self.create_srpm(
                upstream_ref=upstream_ref,
                srpm_dir=self.up.local_project.working_dir,
                release_suffix=release_suffix,
            )

        owner = owner or self.copr_helper.configured_owner
        if not owner:
            raise PackitCoprException(
                "Copr owner not set. Use Copr config file or `--owner` when calling packit CLI."
            )
        logger.info(f"We will operate with COPR owner {owner}.")

        self.copr_helper.create_copr_project_if_not_exists(
            project=project,
            chroots=chroots,
            owner=owner,
            description=description,
            instructions=instructions,
            list_on_homepage=list_on_homepage,
            preserve_project=preserve_project,
            additional_packages=additional_packages,
            additional_repos=additional_repos,
            request_admin_if_needed=request_admin_if_needed,
        )
        logger.debug(
            f"Submitting a build to copr build system,"
            f"owner={owner}, project={project}, path={srpm_path}"
        )

        build = self.copr_helper.copr_client.build_proxy.create_from_file(
            ownername=owner,
            projectname=project,
            path=srpm_path,
            buildopts={"enable_net": enable_net},
        )
        return build.id, self.copr_helper.copr_web_build_url(build)

    def watch_copr_build(
        self, build_id: int, timeout: int, report_func: Callable = None
    ) -> str:
        """returns copr build state"""
        return self.copr_helper.watch_copr_build(
            build_id=build_id, timeout=timeout, report_func=report_func
        )

    def push_bodhi_update(self, update_alias: str):
        """Push selected bodhi update from testing to stable."""
        from bodhi.client.bindings import UpdateNotFound

        bodhi_client = get_bodhi_client(
            fas_username=self.config.fas_user,
            fas_password=self.config.fas_password,
            kerberos_realm=self.config.kerberos_realm,
        )
        # only use Kerberos when fas_user and kerberos_realm are set
        if self.config.fas_user and self.config.kerberos_realm:
            bodhi_client.login_with_kerberos()
        # make sure we have the credentials
        bodhi_client.ensure_auth()
        try:
            response = bodhi_client.request(update=update_alias, request="stable")
            logger.debug(f"Bodhi response:\n{response}")
            response = response["update"]
            logger.info(
                f"Bodhi update {response['alias']} ({response['title']}) pushed to stable:\n"
                f"- {response['url']}\n"
                f"- karma: {response['karma']}\n"
                f"- notes:\n{response['notes']}\n"
            )
        except UpdateNotFound:
            logger.error("Update was not found.")

    def get_testing_updates(self, update_alias: Optional[str]) -> List:
        bodhi_client = get_bodhi_client()
        updates = []
        page = pages = 1
        while page <= pages:
            results = bodhi_client.query(
                alias=update_alias,
                packages=self.dg.package_config.downstream_package_name,
                status="testing",
                page=page,
            )
            updates.extend(results["updates"])
            page += 1
            pages = results["pages"]
        logger.debug("Bodhi updates with status 'testing' fetched.")

        return updates

    @staticmethod
    def days_in_testing(update) -> int:
        if update.get("date_testing"):
            date_testing = datetime.strptime(
                update["date_testing"], "%Y-%m-%d %H:%M:%S"
            )
            return (datetime.utcnow() - date_testing).days
        return 0

    def push_updates(self, update_alias: Optional[str] = None):
        updates = self.get_testing_updates(update_alias)
        if not updates:
            logger.info("No testing updates found.")
        for update in updates:
            if self.days_in_testing(update) >= update["stable_days"]:
                self.push_bodhi_update(update["alias"])
            else:
                logger.debug(f"{update['alias']} is not ready to be pushed to stable")

    def init_kerberos_ticket(self) -> None:
        """
        Initialize the kerberos ticket if we have fas_user and keytab_path configured.

        The `kinit` command is run only once when called multiple times.
        """
        if self._kerberos_initialized:
            return

        if not self.config.pkg_tool.startswith("fedpkg"):
            # centpkg doesn't use kerberos
            return

        if (
            not self.config.fas_user
            or not self.config.keytab_path
            or not Path(self.config.keytab_path).is_file()
        ):
            logger.debug("Won't be doing kinit, no credentials provided.")
            return

        self._run_kinit()
        self._kerberos_initialized = True

    def _run_kinit(self) -> None:
        """Run `kinit`"""
        cmd = [
            "kinit",
            f"{self.config.fas_user}@{self.config.kerberos_realm}",
            "-k",
            "-t",
            self.config.keytab_path,
        ]

        commands.run_command_remote(
            cmd=cmd,
            error_message="Failed to init kerberos ticket:",
            fail=True,
            # this prints debug logs from kerberos to stdout
            env={"KRB5_TRACE": "/dev/stdout"},
        )

    def clean(self):
        """clean up stuff once all the work is done"""
        # this is called in p-s: Handler.clean
        if self.up.is_command_handler_set():
            self.up.command_handler.clean()
        if self.dg.is_command_handler_set():
            self.dg.command_handler.clean()
        if self._up:
            self.up.local_project.free_resources()

    @staticmethod
    def validate_package_config(working_dir: Path) -> str:
        """validate .packit.yaml on the provided path and return human readable report"""
        config_path = find_packit_yaml(
            working_dir,
            try_local_dir_last=True,
        )
        config_content = load_packit_yaml(config_path)
        v = PackageConfigValidator(config_path, config_content, working_dir)
        return v.validate()

    def init_source_git(
        self,
        dist_git: git.Repo,
        source_git: git.Repo,
        upstream_ref: str,
        upstream_url: Optional[str] = None,
        upstream_remote: Optional[str] = None,
        pkg_tool: Optional[str] = None,
        pkg_name: Optional[str] = None,
        ignore_missing_autosetup: bool = False,
    ):
        """
        Initialize a source-git repo from dist-git, that is: add configuration, packaging files
        needed by the distribution and transform the distribution patches into Git commits.

        Args:
            dist_git: Dist-git repository to be used for initialization.
            source_git: Git repository to be initialized as a source-git repo.
            upstream_ref: Upstream ref which is going to be the starting point of the
                source-git history. This can be a branch, tag or commit sha. It is expected
                that the current HEAD and this ref point to the same commit.
            upstream_url: Git URL to be saved in the source-git configuration.
            upstream_remote: Name of the remote from which the fetch URL is taken as the Git URL
                of the upstream project to be saved in the source-git configuration.
            pkg_tool: Packaging tool to be used to interact with the dist-git repo.
            pkg_name: Name of the package in dist-git.
            ignore_missing_autosetup: Do not require %autosetup to be used in the %prep
                section of specfile.
        """
        sgg = SourceGitGenerator(
            config=self.config,
            dist_git=dist_git,
            source_git=source_git,
            upstream_ref=upstream_ref,
            upstream_url=upstream_url,
            upstream_remote=upstream_remote,
            pkg_tool=pkg_tool,
            pkg_name=pkg_name,
            ignore_missing_autosetup=ignore_missing_autosetup,
        )
        sgg.create_from_upstream()

    def run_mock_build(
        self,
        srpm_path: Path,
        root: str = "default",
    ) -> List[Path]:
        """
        Performs a mock build with given SRPM and root.

        Args:
            root: Name of the chroot or path to the mock config.

                Defaults to `"default"` mock config which should be a Fedora
                rawhide.
            srpm_path: Path to the SRPM to be built.

        Returns:
            List of paths to the built RPMs.
        """
        cmd = ["mock", "--root", root, str(srpm_path)]
        escaped_command = " ".join(cmd)
        logger.debug(f"Mock build command: {escaped_command}")

        try:
            cmd_result = self.up.command_handler.run_command(cmd, return_output=True)
        except PackitCommandFailedError as ex:
            logger.error(f"The `mock` command failed: {ex!r}")
            raise PackitFailedToCreateRPMException(
                f"reason:\n"
                f"{ex}\n"
                f"command:\n"
                f"{escaped_command}\n"
                f"stdout:\n"
                f"{ex.stdout_output}\n"
                f"stderr:\n"
                f"{ex.stderr_output}"
            ) from ex
        except PackitException as ex:
            logger.error(f"The `mock` command failed: {ex!r}")
            raise PackitFailedToCreateRPMException(
                f"The `mock` command failed:\n{ex}"
            ) from ex

        rpms = Upstream._get_rpms_from_mock_output(cmd_result.stderr)
        return [Path(rpm) for rpm in rpms]

    def submit_vm_image_build(
        self,
        image_distribution: str,
        image_name: str,
        image_request: Dict,
        image_customizations: Dict,
        copr_namespace: str,
        copr_project: str,
        copr_chroot: str,
    ) -> str:
        """
        Submit a VM image build to Image Builder.

        Documentation:
            https://console.redhat.com/docs/api/image-builder

        Args:
            image_distribution: Distribution of the image (example: rhel-90, rhel-86).
            image_name: Name of the image.
            image_request: Image request definition of an image build, see API reference above.
            image_customizations: Image customizations definition of an image build,
                see API reference above.
            copr_namespace: Copr namespace from which to pick the RPMs from.
            copr_project: Copr project from which to pick the RPMs from.
            copr_chroot: Copr chroot to use for installation of packages.

        Returns:
            Image ID of the submitted image.
        """
        # build_id = self.copr_helper.get_build(build_id=copr_build_id)
        repo_url = self.copr_helper.get_repo_download_url(
            owner=copr_namespace,
            project=copr_project,
            chroot=copr_chroot,
        )
        ib = ImageBuilder(
            refresh_token=self.config.redhat_api_refresh_token,
        )
        return ib.create_image(
            image_distribution=image_distribution,
            image_name=image_name,
            image_request=image_request,
            image_customizations=image_customizations,
            repo_url=repo_url,
        )

    def get_vm_image_build_status(
        self,
        build_id: str,
    ):
        """
        Get the status of a VM image build.

        Args:
            build_id: Build ID of the image.

        Returns:
            Status of the build (example: success, building, pending)
        """
        ib = ImageBuilder(
            refresh_token=self.config.redhat_api_refresh_token,
        )
        return ib.get_image_status(build_id)
