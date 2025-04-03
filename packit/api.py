# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
This is the official python interface for packit.
"""


import asyncio
import contextlib
import copy
import logging
import os
import re
import shlex
import tempfile
from collections.abc import Iterable, Sequence
from datetime import datetime
from distutils.dir_util import copy_tree
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import (
    Callable,
    Literal,
    Optional,
    Union,
    overload,
)

import bugzilla
import click
import git
from git.exc import GitCommandError
from ogr.abstract import PullRequest
from ogr.exceptions import PagureAPIException
from ogr.services.gitlab.project import GitlabProject
from ogr.services.pagure.project import PagureProject
from ogr.services.pagure.pull_request import PagurePullRequest
from tabulate import tabulate

from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.config import Config, PackageConfig, RunCommandType
from packit.config.aliases import get_branches
from packit.config.common_package_config import MockBootstrapSetup, MultiplePackages
from packit.config.package_config import find_packit_yaml, load_packit_yaml
from packit.config.package_config_validator import PackageConfigValidator
from packit.constants import (
    BUGZILLA_HOSTNAME,
    BUGZILLA_URL,
    COMMIT_ACTION_DIVIDER,
    DISTRO_DIR,
    FROM_DIST_GIT_TOKEN,
    FROM_SOURCE_GIT_TOKEN,
    RELEASE_MONITORING_PROJECT_URL,
    REPO_NOT_PRISTINE_HINT,
    SYNC_RELEASE_DEFAULT_COMMIT_DESCRIPTION,
    SYNC_RELEASE_PR_CHECKLIST,
    SYNC_RELEASE_PR_DESCRIPTION,
    SYNC_RELEASE_PR_GITLAB_CLONE_INSTRUCTIONS,
    SYNC_RELEASE_PR_KOJI_NOTE,
    SYNC_RELEASE_PR_PAGURE_CLONE_INSTRUCTIONS,
    SYNCING_NOTE,
)
from packit.copr_helper import CoprHelper
from packit.distgit import DistGit
from packit.exceptions import (
    PackitCommandFailedError,
    PackitCoprException,
    PackitException,
    PackitFailedToCreateRPMException,
    PackitRPMException,
    PackitRPMNotFoundException,
    PackitSRPMException,
    PackitSRPMNotFoundException,
    ReleaseSkippedPackitException,
)
from packit.local_project import LocalProject
from packit.patches import PatchGenerator
from packit.source_git import SourceGitGenerator
from packit.status import Status
from packit.sync import SyncFilesItem, sync_files
from packit.upstream import GitUpstream, NonGitUpstream, Upstream
from packit.utils import commands, obs_helper
from packit.utils.bodhi import get_bodhi_client
from packit.utils.changelog_helper import ChangelogHelper
from packit.utils.extensions import assert_existence
from packit.utils.repo import (
    commit_exists,
    get_commit_diff,
    get_commit_hunks,
    get_commit_link,
    get_commit_message_from_action,
    get_next_commit,
    get_tag_link,
    git_remote_url_to_https_url,
    is_the_repo_pristine,
    shorten_commit_hash,
)
from packit.utils.versions import compare_versions
from packit.vm_image_build import ImageBuilder

logger = logging.getLogger(__name__)

git.Git.GIT_PYTHON_TRACE = "full"


def get_packit_version() -> str:
    try:
        return version("packitos")
    except PackageNotFoundError:
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
        self,
        source_git_range_start: Optional[str],
        dist_git_range_start: Optional[str],
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


def checkout_package_workdir(
    package_config: Optional[Union[PackageConfig, MultiplePackages]],
    local_project: LocalProject,
) -> LocalProject:
    """If local_project is related to a sub-package in a Monorepo
    then fix working dir to point to the sub-package given path.

    Returns:
        A LocalProject with a working dir moved to
        the sub-package path, if a monorepo sub-package,
        otherwise the same local project object.
    """
    if hasattr(package_config, "paths") and package_config.paths and local_project:
        new_local_project = copy.deepcopy(local_project)
        new_local_project.working_dir = new_local_project.working_dir.joinpath(
            package_config.paths[0],
        )
        return new_local_project
    return local_project


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
        non_git_upstream: bool = False,
    ) -> None:
        self.config = config
        self.package_config: MultiplePackages = package_config
        self.upstream_local_project = upstream_local_project
        self.downstream_local_project = downstream_local_project
        self.stage = stage
        self.non_git_upstream = non_git_upstream
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
            self._up = (
                NonGitUpstream(config=self.config, package_config=self.package_config)
                if self.non_git_upstream
                else GitUpstream(
                    config=self.config,
                    package_config=self.package_config,
                    local_project=checkout_package_workdir(
                        self.package_config,
                        self.upstream_local_project,
                    ),
                )
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
                    f"directory name: {self.package_config.downstream_package_name}",
                )
            self._dg = DistGit(
                config=self.config,
                package_config=self.package_config,
                local_project=checkout_package_workdir(
                    self.package_config,
                    self.downstream_local_project,
                ),
                clone_path=self._dist_git_clone_path,
            )
        return self._dg

    @property
    def copr_helper(self) -> CoprHelper:
        if self._copr_helper is None:
            self._copr_helper = CoprHelper(
                upstream_local_project=self.upstream_local_project,
            )
        return self._copr_helper

    def _get_sandcastle_exec_dir(self):
        # import sandcastle here, we don't want to depend upon
        # sandcastle and python-kube if not in service
        from sandcastle.constants import SANDCASTLE_EXEC_DIR

        return SANDCASTLE_EXEC_DIR

    @property
    def pkg_tool(self) -> str:
        """Returns the packaging tool. Prefers the package-level override."""
        if self.package_config and self.package_config.pkg_tool:
            return self.package_config.pkg_tool

        return self.config.pkg_tool

    def common_env(self, version: Optional[str] = None) -> dict[str, str]:
        """
        Constructs an environment with variables that are shared across multiple
        different actions.

        Exposed environment variables:
        * `PACKIT_UPSTREAM_REPO` — path to the upstream repository, if has been
          cloned already
        * `PACKIT_DOWNSTREAM_REPO` — path to the downstream repository, if has
          been cloned already
        * `PACKIT_PROJECT_VERSION` — version for `sync-release` environments, if
          has been provided (see docs/usage for details)
        * `PACKIT_CONFIG_PACKAGE_NAME` — name of the package in the Packit
          config
        * `PACKIT_UPSTREAM_PACKAGE_NAME` — name of the upstream package
        * `PACKIT_DOWNSTREAM_PACKAGE_NAME` — name of the downstream package

        Args:
            version: Optional version to be passed to the environment. Defaults
                to `None` which means that no `PACKIT_PROJECT_VERSION` is
                exposed to the environment.

        Returns:
            Dictionary with environment variables that are exposed to the
            action.
        """
        # Add paths to the repositories
        env = {
            variable_name: str(repo.local_project.working_dir)
            for variable_name, repo in (
                ("PACKIT_DOWNSTREAM_REPO", self.dg),
                ("PACKIT_UPSTREAM_REPO", self.up),
                ("PACKIT_PWD", self.up),
            )
            if isinstance(repo, PackitRepositoryBase)
            and repo._local_project is not None
        }
        if isinstance(self.up, NonGitUpstream):
            env.update({"PACKIT_PWD": str(self.up.working_dir)})

        # Adjust paths for the sandcastle
        if self.config.command_handler == RunCommandType.sandcastle:
            # working dirs should be placed under
            # self.config.command_handler_working_dir
            # when running this code as a service

            exec_dir = Path(self._get_sandcastle_exec_dir())
            for variable in list(env.keys()):
                suffix = Path(env[variable]).relative_to(
                    self.config.command_handler_work_dir,
                )
                env[variable] = str(
                    self.config.command_handler_work_dir / exec_dir / suffix,
                )

        # Add version, if provided
        if version:
            env["PACKIT_PROJECT_VERSION"] = version

        # Add package names
        env |= self.up.package_config.get_package_names_as_env()

        return env

    def update_dist_git(
        self,
        version: Optional[str],
        upstream_ref: Optional[str],
        add_new_sources: bool,
        force_new_sources: bool,
        upstream_tag: Optional[str],
        commit_title: str,
        commit_msg: str,
        pkg_tool: str = "",
        mark_commit_origin: bool = False,
        check_sync_status: bool = False,
        check_dist_git_pristine: bool = True,
        resolved_bugs: Optional[list[str]] = None,
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
            pkg_tool: What tool (fedpkg/centpkg/cbs) to use upload to lookaside cache.
            mark_commit_origin: Whether to include a Git-trailer in the dist-git
                commit message to mark the hash of the upstream (source-git) commit.
            check_sync_status: Check the synchronization status of the source-git
                and dist-git repos prior to performing the update.
            check_dist_git_pristine: Check whether the dist-git is pristine.
            resolved_bugs: List of bugs that are resolved by the update (e.g. [rhbz#123]).
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
            self.dg.local_project.git_repo,
        ):
            raise PackitException(
                "Cannot update the dist-git repo "
                f"{self.dg.local_project.git_repo.working_dir!r}, since it is not pristine."
                f"{REPO_NOT_PRISTINE_HINT}",
            )

        files_to_sync = self.package_config.get_all_files_to_sync()

        self.up.sync_files(files_to_sync, self.dg)

        if self.up.actions_handler.with_action(
            action=ActionName.prepare_files,
            env=self.common_env(version=version),
        ):
            files_to_sync = self._prepare_files_to_sync(
                files_to_sync=files_to_sync,
                full_version=version,
                upstream_tag=upstream_tag,
                resolved_bugs=resolved_bugs,
            )
        else:
            # reload spec files as they could have been changed by the action
            self.up.specfile.reload()
            self.dg.specfile.reload()

        sync_files(files_to_sync)

        # reload the dist-git spec file as it has been most likely synced
        self.dg.specfile.reload()

        if upstream_ref:
            if self.up.actions_handler.with_action(
                action=ActionName.create_patches,
                env=self.common_env(version=version),
            ):
                patches = self.up.create_patches(
                    upstream=upstream_ref,
                    destination=str(self.dg.absolute_specfile_dir),
                )
                # Undo identical patches, but don't remove them
                # from the list, so that they are added to the spec-file.
                PatchGenerator.undo_identical(patches, self.dg.local_project.git_repo)
                self.dg.specfile_add_patches(
                    patches,
                    self.package_config.patch_generation_patch_id_digits,
                )
            else:
                # reload spec files as they could have been changed by the action
                self.up.specfile.reload()
                self.dg.specfile.reload()

        if add_new_sources or force_new_sources:
            self._handle_sources(
                force_new_sources=force_new_sources,
                pkg_tool=pkg_tool,
                env=self.common_env(version=version),
            )
        else:
            # run the `post-modifications` action even if sources are not being processed
            self.up.actions_handler.run_action(
                actions=ActionName.post_modifications,
                env=self.common_env(version=version),
            )
            # reload spec files as they could have been changed by the action
            self.up.specfile.reload()
            self.dg.specfile.reload()

        if commit_title:
            trailers = (
                [
                    (
                        FROM_SOURCE_GIT_TOKEN,
                        self.up.local_project.git_repo.head.commit.hexsha,
                    ),
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
    def _transform_patch_to_source_git(patch: str, diffs: list[git.Diff]) -> str:
        """Transforms a dist-git patch to source-git.

        It's necessary to insert .distro directory to paths in the patch.
        """
        for diff in diffs:
            if diff.a_path:
                patch = patch.replace(
                    f"a/{diff.a_path}",
                    f"a/{DISTRO_DIR}/{diff.a_path}",
                )
            if diff.b_path:
                patch = patch.replace(
                    f"b/{diff.b_path}",
                    f"b/{DISTRO_DIR}/{diff.b_path}",
                )
        return patch

    def update_source_git(
        self,
        revision_range: Optional[str] = None,
        check_sync_status: bool = True,
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
                "revision_range has to be specified if check_sync_status is False",
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
                    f"revision_range not specified, setting to {revision_range}",
                )

        if not is_the_repo_pristine(self.up.local_project.git_repo):
            raise PackitException(
                "Cannot update the source-git repo "
                f"{self.up.local_project.git_repo.working_dir!r}, since it is not pristine."
                f"{REPO_NOT_PRISTINE_HINT}",
            )

        dg_release = self.dg.specfile.expanded_release
        up_release = self.up.specfile.expanded_release
        if dg_release != up_release:
            logger.info(
                f"Release differs between dist-git and source-git ("
                f"{dg_release} in dist-git and {up_release} in source-git). "
                f"Trying to continue with the update.",
            )

        # Do the checks beforehand but store commits and diffs to avoid recomputing.
        # Getting patch of a git commit is costly as per GitPython docs.
        commits: list[git.Commit] = []
        diffs: list[list[git.Diff]] = []
        patch_suffix = ".patch"
        distro_path = self.up.local_project.working_dir / DISTRO_DIR
        for commit in self.dg.local_project.git_repo.iter_commits(
            revision_range,
            reverse=True,
        ):
            commits.append(commit)
            diffs.append(get_commit_diff(commit))
            for diff in diffs[-1]:
                if diff.a_path == "sources" or diff.b_path == "sources":
                    raise PackitException(
                        f"The sources file was modified in commit "
                        f"{commit.hexsha} which is part of the provided range. "
                        f"Such operation is not supported.",
                    )
                a_path = diff.a_path or ""
                b_path = diff.b_path or ""
                # FIXME: this check is not great, but if we want to be more precise, we would
                #   have to parse the spec in each checkout of dist-git
                if a_path.endswith(patch_suffix) or b_path.endswith(patch_suffix):
                    raise PackitException(
                        f"A patch was modified in commit {commit.hexsha} "
                        f"which is not supported by this command.",
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
                    with contextlib.suppress(FileNotFoundError):
                        path.unlink()
                elif diff.renamed_file:
                    path = distro_path / diff.a_path
                    try:
                        path.rename(distro_path / Path(diff.b_path).name)
                    except FileNotFoundError as e:
                        raise PackitException(
                            f"File {diff.a_path} to be renamed does not exist in source-git.",
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
                                    f"change, skipping this part of the commit.",
                                )
                                continue
                            raise PackitException(
                                f"Commit {commit} could not be applied to source-git.",
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
                    f"Commit {commit} had no changes to be applied, skipping it.",
                )

    def _get_latest_commit_update_pair(self) -> tuple[str, str]:
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
                max_count=1,
                grep=rf"^{re.escape(FROM_DIST_GIT_TOKEN)}: .\+$",
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
                max_count=1,
                grep=rf"^{re.escape(FROM_SOURCE_GIT_TOKEN)}: .\+$",
            )
        ]
        if sg_update_commits and not commit_exists(
            self.dg.local_project.git_repo,
            sg_update_commits[0][1],
        ):
            raise PackitException(
                f"Commit '{sg_update_commits[0][1]}' referenced in {FROM_DIST_GIT_TOKEN} "
                f"git trailer does not exist in dist-git.",
            )
        if dg_update_commits and not commit_exists(
            self.up.local_project.git_repo,
            dg_update_commits[0][0],
        ):
            raise PackitException(
                f"Commit '{dg_update_commits[0][0]}' referenced in {FROM_SOURCE_GIT_TOKEN} "
                f"git trailer does not exist in source-git.",
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
                sg_update_commits[0][0],
                dg_update_commits[0][0],
            ):
                return dg_update_commits[0]
            return sg_update_commits[0]
        if sg_update_commits:
            return sg_update_commits[0]
        if dg_update_commits:
            return dg_update_commits[0]
        raise PackitException(
            "No git commits with trailers to mark synchronization points were found.",
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
                self.up.local_project.git_repo,
                sg_sync_point,
            ),
            dist_git_range_start=get_next_commit(
                self.dg.local_project.git_repo,
                dg_sync_point,
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
The first source-git commit to be synced is '{shorten_commit_hash(status.source_git_range_start)}'.
The first dist-git commit to be synced is '{shorten_commit_hash(status.dist_git_range_start)}'.
Sync status needs to be reestablished manually, see
https://packit.dev/source-git/work-with-source-git/fix-diverged-history
"""
        if status.source_git_range_start:
            number_of_commits = len(
                list(
                    self.up.local_project.git_repo.iter_commits(
                        f"{status.source_git_range_start}~..",
                        ancestry_path=True,
                    ),
                ),
            )
            return f"""'{source_git}' is ahead of '{dist_git}' by {number_of_commits} commits.
Use "packit source-git update-dist-git {source_git} {dist_git}"
to transform changes from '{source_git}' to '{dist_git}'.
The first source-git commit to be synced is '{shorten_commit_hash(status.source_git_range_start)}'.
"""
        if status.dist_git_range_start:
            number_of_commits = len(
                list(
                    self.dg.local_project.git_repo.iter_commits(
                        f"{status.dist_git_range_start}~..",
                        ancestry_path=True,
                    ),
                ),
            )
            short_hash = shorten_commit_hash(status.dist_git_range_start)
            return f"""'{source_git}' is behind of '{dist_git}' by {number_of_commits} commits.
Use "packit source-git update-source-git {dist_git} {source_git}
{short_hash}~..\" to transform changes from '{dist_git}' to '{source_git}'.
The first dist-git commit to be synced is '{short_hash}'.
"""
        return f"'{source_git}' is up to date with '{dist_git}'."

    def check_version_distance(
        self,
        current,
        proposed,
        target_branch,
    ) -> bool:
        """Following this guidelines:
        https://docs.fedoraproject.org/en-US/fesco/Updates_Policy/#philosophy
        https://docs.fedoraproject.org/en-US/epel/epel-policy-updates/
        we want to avoid major updates of packages within a **stable** release.

        current: str, already released version for package
        proposed: str, release we are preparing for package
        target_branch: str, Fedora branch where release the package
        """
        branches_to_check = get_branches("fedora-branched").union(
            get_branches("epel-all"),
        )
        if (
            self.package_config.version_update_mask
            and target_branch in branches_to_check
        ):
            masked_current = re.match(self.package_config.version_update_mask, current)
            masked_proposed = re.match(
                self.package_config.version_update_mask,
                proposed,
            )
            if (
                masked_current
                and masked_proposed
                and masked_current.group(0) != masked_proposed.group(0)
            ):
                logger.debug(
                    f"Masked {current} and {proposed} ({masked_current} and {masked_proposed}) "
                    f"do not match.",
                )
                return False
        return True

    @staticmethod
    def get_upstream_release_monitoring_bug(
        package_name: str,
        version: str,
    ) -> Optional[str]:
        """
        Obtain the bug created by Upstream Release Monitoring
        about the new upstream release matching the package_name
        and the version via Bugzilla API.

        Returns bugzilla if found in format 'rhbz#{id}'
        """
        bzapi = bugzilla.Bugzilla(BUGZILLA_HOSTNAME)
        # https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug.html#search-bugs
        query = {
            "product": ["Fedora"],
            "component": [package_name],
            "bug_status": "NEW",
            # e.g. python-ogr-50.1 is available
            "summary": "is available",
            "creator": "Upstream Release Monitoring",
        }
        logger.debug(
            f"About to search for Bugzilla bugs with these parameters: {query}",
        )
        try:
            bugs = bzapi.query(query)
        except Exception as ex:
            logger.error(f"There was an error when calling Bugzilla API: {ex!r}")
            return None

        logger.debug(
            f"Bugzilla IDs found via Bugzilla API: {[bug.id for bug in bugs]}",
        )

        if bugs:
            logger.debug(f"About to find the bug matching version {version}")

        for bug in bugs:
            match = re.search(f"{package_name}-(.*?) is available", bug.summary)
            if match and match.group(1) == version:
                logger.debug(f"Found matching bug with ID {bug.id}")
                return f"rhbz#{bug.id}"

        return None

    @overload
    def sync_release(
        self,
        dist_git_branch: Optional[str] = None,
        versions: Optional[list[str]] = None,
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
        local_pr_branch_suffix: str = "update",
        mark_commit_origin: bool = False,
        use_downstream_specfile: bool = False,
        add_pr_instructions: bool = False,
        resolved_bugs: Optional[list[str]] = None,
        release_monitoring_project_id: Optional[int] = None,
        pr_description_footer: Optional[str] = None,
        sync_acls: Optional[bool] = False,
        fast_forward_merge_branches: Optional[set[str]] = None,
        warn_about_koji_build_triggering_bug: bool = False,
    ) -> tuple[PullRequest, dict[str, PullRequest]]:
        """Overload for type-checking; return PullRequest if create_pr=True."""

    @overload
    def sync_release(
        self,
        dist_git_branch: Optional[str] = None,
        versions: Optional[list[str]] = None,
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
        local_pr_branch_suffix: str = "update",
        mark_commit_origin: bool = False,
        use_downstream_specfile: bool = False,
        add_pr_instructions: bool = False,
        resolved_bugs: Optional[list[str]] = None,
        release_monitoring_project_id: Optional[int] = None,
        pr_description_footer: Optional[str] = None,
        sync_acls: Optional[bool] = False,
        fast_forward_merge_branches: Optional[set[str]] = None,
        warn_about_koji_build_triggering_bug: bool = False,
    ) -> None:
        """Overload for type-checking; return None if create_pr=False."""

    def sync_release(
        self,
        dist_git_branch: Optional[str] = None,
        versions: Optional[list[str]] = None,
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
        local_pr_branch_suffix: str = "update",
        mark_commit_origin: bool = False,
        use_downstream_specfile: bool = False,
        add_pr_instructions: bool = False,
        resolved_bugs: Optional[list[str]] = None,
        release_monitoring_project_id: Optional[int] = None,
        pr_description_footer: Optional[str] = None,
        sync_acls: Optional[bool] = False,
        fast_forward_merge_branches: Optional[set[str]] = None,
        warn_about_koji_build_triggering_bug: bool = False,
    ) -> Optional[tuple[PullRequest, dict[str, PullRequest]]]:
        """
        Update given package in dist-git

        Args:
            dist_git_branch: Branch in dist-git, defaults to repo's default branch.
            use_local_content: Don't check out anything.
            versions: List of new upstream versions.
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
            local_pr_branch_suffix: When create_pr is True, we push into a newly created
                branch and create a PR from it. This param specifies a suffix attached
                to the created branch name, so that we can have more PRs for the same
                dg branch at one time.
            mark_commit_origin: Whether to include a Git-trailer in the dist-git
                commit message to mark the hash of the upstream (source-git) commit.
            use_downstream_specfile: Use the downstream specfile instead
                of getting the upstream one (used by packit-service in pull_from_upstream)
            add_pr_instructions: Whether to add instructions on how to change the content
                of the created PR (used by packit-service)
            resolved_bugs: List of bugs that are resolved by the update (e.g. [rhbz#123]).
            release_monitoring_project_id: ID of the project in release monitoring if the syncing
                happens as reaction to that.
            pr_description_footer: Footer for the PR description (used by packit-service)
            sync_acls: Whether to sync the ACLs of original repo and
                fork when creating a PR from fork.
            fast_forward_merge_branches: Set of branches `dist_git_branch` should be
                fast-forward-merged into.

        Returns:
            Tuple of the created (or existing if one already exists) PullRequest and
             dictionary of branches from fast_forward_merge_branches as keys and
             PullRequest objects as values if
            create_pr is True, else None.

        Raises:
            PackitException, if both 'version' and 'tag' are provided.
            PackitException, if the version of the latest upstream release cannot be told.
            PackitException, if the upstream repo or dist-git is dirty.
        """
        dist_git_branch = (
            dist_git_branch or self.dg.local_project.git_project.default_branch
        )
        version = None
        # process versions and tag parameters
        if versions and tag:
            raise PackitException(
                "Function parameters versions and tag are mutually exclusive.",
            )
        if not tag:
            # [FIXME] for now let's just pick the first one
            version = versions[0] if versions else self.up.get_latest_released_version()
            if not version:
                raise PackitException(
                    "Could not figure out version of latest upstream release. "
                    "You can specify it as an argument.",
                )
            upstream_tag = self.up.convert_version_to_tag(version)
        else:
            upstream_tag = tag
            version = self.up.get_version_from_tag(tag)

        if isinstance(self.up, GitUpstream):
            assert_existence(self.up.local_project, "Upstream local project")

        assert_existence(self.dg.local_project, "Dist-git local project")
        if self.dg.is_dirty():
            raise PackitException(
                f"The distgit repository {self.dg.local_project.working_dir} is dirty."
                f"This is not supported.",
            )
        if not force and self.up.is_dirty() and not use_local_content:
            raise PackitException(
                "The repository is dirty, will not discard the changes. Use --force to bypass.",
            )
        upstream_ref = self.up._expand_git_ref(
            upstream_ref or self.package_config.upstream_ref,
        )
        # don't reference Upstream Release Monitoring bug for CentOS
        if not resolved_bugs and self.package_config.pkg_tool in (None, "fedpkg"):
            upstream_release_monitoring_bug = self.get_upstream_release_monitoring_bug(
                package_name=self.dg.local_project.repo_name,
                version=version,
            )
            resolved_bugs = (
                [upstream_release_monitoring_bug]
                if upstream_release_monitoring_bug
                else []
            )

        current_up_branch = self.up.active_branch
        try:
            # we want to check out the tag only when local_content is not set
            # and it's an actual upstream repo and not source-git
            if upstream_ref:
                logger.info(
                    "We will not check out the upstream tag "
                    "because this is a source-git repo.",
                )
            elif not use_local_content:
                self.up.checkout_release(upstream_tag)

            self.dg.create_branch(
                dist_git_branch,
                base=f"remotes/origin/{dist_git_branch}",
                setup_tracking=True,
            )
            # fetch and reset --hard upstream/$branch?
            logger.info(f"Using {dist_git_branch!r} dist-git branch.")
            self.dg.update_branch(dist_git_branch)
            self.dg.switch_branch(dist_git_branch, force=True)

            # do not add anything between distgit clone/checkout and saving gpg keys!
            self.up.allowed_gpg_keys = (
                self.dg.get_allowed_gpg_keys_from_downstream_config()
            )

            try:
                downstream_spec_ver = self.dg.get_specfile_version()
                if compare_versions(version, downstream_spec_ver) < 0:
                    msg = (
                        f"Downstream specfile version {downstream_spec_ver} is higher "
                        f"than the version to propose ({version}). Skipping the update."
                    )
                    logger.debug(msg)
                    raise ReleaseSkippedPackitException(msg)
                self.dg.refresh_specfile()

            except FileNotFoundError:
                # no downstream spec file
                pass

            if use_downstream_specfile:
                logger.info(
                    "Using the downstream specfile instead of the upstream one.",
                )
                self.up.set_specfile(self.dg.specfile)

            self.up.actions_handler.run_action(
                actions=ActionName.post_upstream_clone,
                env=self.common_env(version=version),
            )

            # reload spec files as they could have been changed by the action
            self.up.specfile.reload()
            # downstream spec file doesn't have to exist yet
            with contextlib.suppress(FileNotFoundError):
                self.dg.specfile.reload()

            # compare versions here because users can mangle with specfile in
            # post_upstream_clone action
            spec_ver = self.up.get_specfile_version()
            if compare_versions(version, spec_ver) > 0:
                logger.warning(f"Version {spec_ver!r} in spec file is outdated.")

            if not self.check_version_distance(version, spec_ver, dist_git_branch):
                raise ReleaseSkippedPackitException(
                    f"The upstream released version {version} does not match "
                    f"specfile version {spec_ver} at branch {dist_git_branch} "
                    f"using the version_update_mask "
                    f'"{self.package_config.version_update_mask}".'
                    "\nYou can change the version_update_mask with an empty string "
                    "to skip this check.",
                )

            self.dg.check_last_commit()

            self.up.actions_handler.run_action(
                actions=ActionName.pre_sync,
                env=self.common_env(version=version),
            )

            # reload spec files as they could have been changed by the action
            self.up.specfile.reload()
            # downstream spec file doesn't have to exist yet
            with contextlib.suppress(FileNotFoundError):
                self.dg.specfile.reload()

            if create_pr:
                local_pr_branch = f"{dist_git_branch}-{local_pr_branch_suffix}"
                self.dg.create_branch(
                    local_pr_branch,
                )
                self.dg.switch_branch(local_pr_branch, force=True)
                self.dg.reset_workdir()
                self.dg.rebase_branch(dist_git_branch)

            if create_sync_note and self.package_config.create_sync_note:
                readme_path = self.dg.local_project.working_dir / "README.packit"
                logger.debug(f"README: {readme_path}")
                readme_path.write_text(
                    SYNCING_NOTE.format(packit_version=get_packit_version()),
                )

            # Preset the PR title and instructions
            pr_title = (
                title or f"Update {dist_git_branch} to upstream release {version}"
            )

            # Evaluate the commit title and message
            commit_msg_action_output = self.up.actions_handler.get_output_from_action(
                ActionName.commit_message,
                env={
                    "PACKIT_UPSTREAM_TAG": upstream_tag,
                    "PACKIT_UPSTREAM_COMMIT": self.up.commit_hexsha,
                    "PACKIT_DEBUG_DIVIDER": COMMIT_ACTION_DIVIDER.strip(),
                    "PACKIT_RESOLVED_BUGS": (
                        " ".join(resolved_bugs) if resolved_bugs else ""
                    ),
                }
                | self.common_env(version),
            )

            commit_title, commit_description = get_commit_message_from_action(
                output=commit_msg_action_output,
                default_title=title or f"Update to {version} upstream release",
                default_description=description
                or self.get_default_commit_description(upstream_tag, resolved_bugs),
            )

            self.update_dist_git(
                version,
                upstream_ref,
                add_new_sources=add_new_sources,
                force_new_sources=force_new_sources,
                upstream_tag=upstream_tag,
                commit_title=commit_title,
                commit_msg=commit_description,
                mark_commit_origin=mark_commit_origin,
                check_dist_git_pristine=False,
                resolved_bugs=resolved_bugs,
            )

            pr = None
            ff_prs = {}

            if create_pr:
                pr_description = self.get_pr_description(
                    upstream_tag=upstream_tag,
                    release_monitoring_project_id=release_monitoring_project_id,
                    resolved_bugs=resolved_bugs,
                )
                pr_instructions = (
                    f"\n---\n\n{self.get_pr_instructions(local_pr_branch=local_pr_branch)}\n"
                    if add_pr_instructions
                    else ""
                )
                footer = (
                    f"\n---\n\n{pr_description_footer}" if pr_description_footer else ""
                )
                pr = self.push_and_create_pr(
                    pr_title=pr_title,
                    pr_description=f"{pr_description}{pr_instructions}{footer}",
                    git_branch=dist_git_branch,
                    repo=self.dg,
                    sync_acls=sync_acls,
                )

                if fast_forward_merge_branches:
                    for ff_branch in fast_forward_merge_branches:
                        logger.info(
                            f"Syncing branch {ff_branch} defined in `fast_forward_merge_into`",
                        )
                        self.dg.refresh_specfile()
                        self.dg.create_branch(
                            ff_branch,
                            base=f"remotes/origin/{ff_branch}",
                            setup_tracking=True,
                        )
                        self.dg.update_branch(ff_branch)
                        self.dg.switch_branch(ff_branch, force=True)

                        try:
                            spec_ver = self.dg.get_specfile_version()
                        except FileNotFoundError:
                            continue

                        self.dg.switch_branch(local_pr_branch, force=True)

                        if not self.check_version_distance(
                            version,
                            spec_ver,
                            ff_branch,
                        ):
                            logger.info(
                                f"The upstream released version {version} does not match "
                                f"specfile version {spec_ver} at branch {ff_branch} "
                                f"using the version_update_mask "
                                f'"{self.package_config.version_update_mask}".'
                                "\nYou can change the version_update_mask with an empty string "
                                "to skip this check.",
                            )
                            continue

                        pr_title = (
                            title or f"Update {ff_branch} to upstream release {version}"
                        )
                        ff_branch_pr = self.create_or_update_pr(
                            pr_title=pr_title,
                            pr_description=f"{pr_description}{pr_instructions}{footer}",
                            target_branch=ff_branch,
                            repo=self.dg,
                        )
                        ff_prs[ff_branch] = ff_branch_pr
                        if warn_about_koji_build_triggering_bug:
                            self._warn_about_koji_build_triggering_bug_if_needed(
                                ff_branch_pr,
                            )

                if warn_about_koji_build_triggering_bug:
                    self._warn_about_koji_build_triggering_bug_if_needed(pr)
            else:
                self.dg.push(refspec=f"HEAD:{dist_git_branch}")
        finally:
            # version should hold the plain version string
            if version.startswith("v"):
                logger.warning(
                    "Please, check whether the `upstream_tag_template` needs to be configured.",
                )
            if not use_local_content and not upstream_ref and current_up_branch:
                logger.info(f"Checking out the original branch {current_up_branch}.")
                self.up.local_project.git_repo.git.checkout(current_up_branch, "-f")
            self.dg.refresh_specfile()
            self.dg.local_project.git_repo.git.reset("--hard", "HEAD")
            self.dg.local_project.git_repo.git.clean("-xdf")
            self.up.clean_working_dir()

        return pr, ff_prs if create_pr else None

    def get_default_commit_description(
        self,
        upstream_tag: str,
        resolved_bugs: Optional[list[str]],
    ) -> str:
        """
        Get the default commit description.
        In case the autochangelog is used, the bugs should be referenced in the commits.
        """
        resolved_bugs_msg = ""
        # https://docs.pagure.org/Fedora-Infra.rpmautospec/autochangelog.html#
        # changelog-entries-generated-from-commit-messages
        # for autochangelog generated from commits, the text that
        # should be included needs to be prefixed with dash
        if resolved_bugs:
            for bug in resolved_bugs:
                resolved_bugs_msg += f"- Resolves: {bug}\n"
            # add one more newline so that the text after is not included in autochangelog
            resolved_bugs_msg += "\n"

        upstream_commit_info = (
            f"Upstream commit: {self.up.commit_hexsha}" if self.up.commit_hexsha else ""
        )
        upstream_tag_info = (
            f"Upstream tag: {upstream_tag}"
            if not isinstance(self.up, NonGitUpstream)
            else ""
        )

        return SYNC_RELEASE_DEFAULT_COMMIT_DESCRIPTION.format(
            upstream_tag=upstream_tag_info,
            upstream_commit_info=upstream_commit_info,
            resolved_bugs=resolved_bugs_msg,
        )

    def get_pr_description(
        self,
        upstream_tag: str,
        release_monitoring_project_id: Optional[int] = None,
        resolved_bugs: Optional[list[str]] = None,
    ) -> str:
        """
        Get the description used in pull requests for syncing release.
        """
        resolved_bugzillas_info = ""
        if resolved_bugs:
            for bug in resolved_bugs:
                match = re.search(r"#(\d+)", bug)
                if match:
                    bug_id = match.group(1)
                    resolved_bugzillas_info += (
                        f"Resolves: [{bug}]({BUGZILLA_URL.format(bug_id=bug_id)})\n"
                    )
                else:
                    resolved_bugzillas_info += f"Resolves: {bug}\n"

        commit = self.up.commit_hexsha

        if self.up.local_project:
            git_url = git_remote_url_to_https_url(
                self.up.local_project.git_url,
                with_dot_git_suffix=False,
            )

            tag_link = get_tag_link(git_url, upstream_tag)
        else:
            tag_link = None

        if commit:
            commit_link = get_commit_link(git_url, commit)
            commit_info = f"[{commit}]({commit_link})" if commit_link else commit
            commit_info = f"Upstream commit: {commit_info}"
        else:
            commit_info = ""

        tag_link = f"[{upstream_tag}]({tag_link})" if tag_link else upstream_tag
        release_monitoring_info = (
            (
                f"Release monitoring project: "
                f"[{release_monitoring_project_id}]"
                f"({RELEASE_MONITORING_PROJECT_URL.format(project_id=release_monitoring_project_id)})\n"
            )
            if release_monitoring_project_id
            else ""
        )
        tag_info = (
            f"Upstream tag: {tag_link}"
            if not isinstance(self.up, NonGitUpstream)
            else ""
        )

        return SYNC_RELEASE_PR_DESCRIPTION.format(
            upstream_tag_info=tag_info,
            upstream_commit_info=commit_info,
            release_monitoring_info=release_monitoring_info,
            resolved_bugzillas_info=resolved_bugzillas_info,
        )

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

    def get_pr_instructions(self, local_pr_branch: str) -> str:
        """
        Get instructions for the update that will be included in the PR description.

        Args:
            local_pr_branch: PR branch for local checkout

        Returns: instructions to include in PR
        """
        instructions: list[str] = []
        if isinstance(self.dg.local_project.git_project, PagureProject):
            instructions.append(
                SYNC_RELEASE_PR_PAGURE_CLONE_INSTRUCTIONS.format(
                    package=self.dg.local_project.repo_name,
                    branch=local_pr_branch,
                    user=self.config.fas_user,
                ),
            )
            # TODO once Koji builds work for GitLab, this should be handled differently
            instructions.append(SYNC_RELEASE_PR_KOJI_NOTE)

        if isinstance(self.dg.local_project.git_project, GitlabProject):
            instructions.append(SYNC_RELEASE_PR_GITLAB_CLONE_INSTRUCTIONS)

        instructions.append(SYNC_RELEASE_PR_CHECKLIST)

        return "\n\n---\n\n".join(instruction for instruction in instructions)

    def sync_push(
        self,
        dist_git_branch: Optional[str] = None,
        source_git_branch: Optional[str] = None,
        create_pr: bool = True,
        title: Optional[str] = None,
        description: Optional[str] = None,
        force: bool = False,
    ) -> Optional[PullRequest]:
        """
        When dist-git is updated then update the source-git repository by opening a PR.

        Args:
            dist_git_branch: Dist-git branch, defaults to repo's default branch.
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
        # this should not be even reachable, just to satisfy mypy
        if not isinstance(self.up, GitUpstream):
            logger.debug("Syncing not allowed for non-git upstream.")
            return None

        assert_existence(self.up.local_project, "Upstream local project")
        assert_existence(self.dg.local_project, "Dist-git local project")

        if self.up.is_dirty():
            raise PackitException(
                f"The upstream repository {self.up.local_project.working_dir} is dirty."
                f"This is not supported.",
            )
        if not force and self.dg.is_dirty():
            raise PackitException(
                f"The distgit repository {self.up.local_project.working_dir} is dirty,"
                " will not discard the changes. Use --force to bypass.",
            )

        dist_git_branch = (
            dist_git_branch or self.dg.local_project.git_project.default_branch
        )
        source_git_branch = (
            source_git_branch or self.up.local_project.git_project.default_branch
        )

        pr = None
        try:
            self.dg.switch_branch(dist_git_branch)
            self.up.switch_branch(source_git_branch)
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
        self,
        files_to_sync: list[SyncFilesItem],
        full_version: str,
        upstream_tag: str,
        resolved_bugs: Optional[list[str]] = None,
    ) -> list[SyncFilesItem]:
        """
        Returns the list of files to sync to dist-git as is.

        With spec-file, we have two modes:
        * The `sync_changelog` option is set. => Spec-file can be synced as other files.
        * Sync the content of the spec-file (but changelog) here and exclude spec-file otherwise.

        Args:
            files_to_sync: A list of SyncFilesItem.
            full_version: Version to be set in the spec-file.
            upstream_tag: The commit message of this commit is going to be used
                to update the changelog in the spec-file.
            resolved_bugs: List of bugs that are resolved by the update (e.g. [rhbz#123]).

        Returns:
            The list of synced files with the spec-file removed if it was updated.
        """
        if self.package_config.sync_changelog:
            return files_to_sync

        # add entry to changelog
        ChangelogHelper(self.up, self.dg, self.package_config).update_dist_git(
            full_version=full_version,
            upstream_tag=upstream_tag,
            resolved_bugs=resolved_bugs,
        )

        # exclude spec, we have special plans for it
        return list(
            filter(
                None,
                [
                    x.drop_src(self.up.get_absolute_specfile_path())
                    for x in files_to_sync
                ],
            ),
        )

    def sync_from_downstream(
        self,
        dist_git_branch: Optional[str] = None,
        upstream_branch: Optional[str] = None,
        no_pr: bool = False,
        fork: bool = True,
        remote_name: Optional[str] = None,
        exclude_files: Optional[Iterable[str]] = None,
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
                "The repository is dirty, will not discard the changes. Use --force to bypass.",
            )
        self.dg.update_branch(dist_git_branch)
        self.dg.switch_branch(dist_git_branch)

        logger.info(f"Using {dist_git_branch!r} dist-git branch.")

        if no_pr:
            self.up.switch_branch(upstream_branch)
        else:
            local_pr_branch = f"{dist_git_branch}-downstream-sync"
            self.up.create_branch(local_pr_branch)
            self.up.switch_branch(local_pr_branch)

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

    def create_or_update_pr(
        self,
        pr_title: str,
        pr_description: str,
        target_branch: str,
        repo: Union[GitUpstream, DistGit],
    ) -> PullRequest:
        pr = repo.existing_pr(
            target_branch,
            repo.local_project.ref,
        )
        if pr is None:
            pr = repo.create_pull(
                pr_title,
                pr_description,
                source_branch=repo.local_project.ref,
                target_branch=target_branch,
            )
        else:
            logger.debug(
                f"PR already exists: {pr.url},"
                f' updating title ("{pr_title}") and description',
            )
            try:
                pr.update_info(pr_title, pr_description)
            except PagureAPIException as exc:
                logger.error(f"Update of existing PR {pr.url} failed: {exc}")
                raise PackitException(f"Update of existing PR {pr.url} failed") from exc
        return pr

    def _warn_about_koji_build_triggering_bug_if_needed(self, pr: PullRequest) -> None:
        """
        Adds a warning comment to a Pagure PR that is susceptible to a bug that breaks
        Koji build triggering.

        This method can be removed after https://github.com/packit/packit-service/issues/2537
        is resolved.

        Args:
            pr: Newly created or updated pull request object.
        """
        if not isinstance(pr, PagurePullRequest):
            logger.debug("Not a Pagure PR, skipping the warning comment.")
            return

        if pr._raw_pr["commit_start"] == pr._raw_pr["commit_stop"]:
            # PR contains single commit
            return

        pr.comment(
            "**Warning**\n"
            "As this pull request contains more than one commit, you may be affected "
            "by a [bug](https://github.com/packit/packit-service/issues/2537) "
            "that will prevent the configured `koji_build` job(s) from being triggered "
            "after this pull request is merged. If that happens, please [trigger the job manually]"
            "(https://packit.dev/docs/fedora-releases-guide/dist-git-onboarding#retriggering).",
        )

    def push_and_create_pr(
        self,
        pr_title: str,
        pr_description: str,
        git_branch: str,
        repo: Union[GitUpstream, DistGit],
        sync_acls: bool = False,
    ) -> PullRequest:
        # the branch may already be up, let's push forcefully
        try:
            repo.push_to_fork(repo.local_project.ref, force=True, sync_acls=sync_acls)
        except PackitException as exc:
            logger.error(f"Push to fork failed: {exc}")
            raise
        return self.create_or_update_pr(
            pr_title,
            pr_description,
            target_branch=git_branch,
            repo=repo,
        )

    def _handle_sources(
        self,
        force_new_sources: bool,
        pkg_tool: str = "",
        env: Optional[dict] = None,
    ):
        """Download upstream archive and upload it to dist-git lookaside cache.

        Args:
            force_new_sources: Download/upload the archive even if it's
                name is already in the cache or in sources file.
                Actually, fedpkg/centpkg/cbs won't upload it if archive with the same
                name & hash is already there, so this might be useful only if
                you want to upload archive with the same name but different hash.
            pkg_tool: Tool to upload sources.
            env: Environment to pass to the `post-modifications` action.
        """
        # We need to download the sources beforehand! Previous solution was relying
        # on the HTTP index of the uploaded archives in the lookaside cache which
        # appears to be Fedora-only. Making the check distro-agnostic requires us
        # to use the `pyrpkg` which needs hash of the archive when doing the lookup,
        # therefore it needs the archive itself beforehand.
        upstream_archives = self.dg.download_upstream_archives()

        # Filter out git-tracked upstream archives
        untracked_upstream_archives = [
            archive
            for archive in upstream_archives
            if str(archive.relative_to(self.dg.absolute_source_dir))
            not in self.dg.git_tracked_files
        ]

        self.up.actions_handler.run_action(
            actions=ActionName.post_modifications,
            env=env,
        )

        # reload spec files as they could have been changed by the action
        self.up.specfile.reload()
        self.dg.specfile.reload()

        # Check for existing local archives and upload those as well
        local_archives = self.get_local_archives_to_upload()

        archives = untracked_upstream_archives + local_archives

        if (
            not self.should_archives_be_uploaded_to_lookaside(archives)
            and not force_new_sources
        ):
            return

        # There is at least one archive to upload,
        # because it is missing from lookaside, sources file, or both,
        # or because force_new_sources is set.
        self.init_kerberos_ticket()
        # Upload all of archives. If we uploaded only those that need uploading,
        # we would lose the unchanged ones from sources file,
        # because upload_to_lookaside_cache maintains the sources file in addition
        # to uploading, and it replaces it entirely, losing the previous content
        self.dg.upload_to_lookaside_cache(
            archives=archives,
            pkg_tool=pkg_tool,
            offline=not self.package_config.upload_sources,
        )

    def should_archives_be_uploaded_to_lookaside(self, archives: list[Path]) -> bool:
        # Here, dist-git spec-file has already been updated from the upstream spec-file.
        # => Any update done to the Source tags in upstream
        # is already available in the dist-git spec-file.
        sources_file = self.dg.local_project.working_dir / "sources"
        for archive in archives:
            archive_name = os.path.basename(archive)
            archive_name_in_cache = self.dg.is_archive_in_lookaside_cache(
                archive,
            )
            archive_name_in_sources_file = (
                sources_file.is_file() and archive_name in sources_file.read_text()
            )

            if not archive_name_in_cache or not archive_name_in_sources_file:
                return True

        return False

    def get_local_archives_to_upload(self) -> list[Path]:
        local_archives = self.dg.local_archive_names
        local_archives_to_upload = []
        for local_archive in local_archives:
            archive_path = self.dg.absolute_source_dir / local_archive
            if not archive_path.exists() or local_archive in self.dg.git_tracked_files:
                logger.debug(
                    f"Local archive {archive_path} doesn't exist or is tracked by git. "
                    f"Skipping the handling of it.",
                )
                continue
            local_archives_to_upload.append(archive_path)

        return local_archives_to_upload

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

        Returns:
            The 'stdout' of the build command.
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
        self.dg.switch_branch(dist_git_branch)

        return self.dg.build(scratch=scratch, nowait=nowait, koji_target=koji_target)

    def create_update(
        self,
        dist_git_branch: str,
        update_type: str,
        update_notes: Optional[str] = None,
        koji_builds: Optional[Sequence[str]] = None,
        sidetag: Optional[str] = None,
        bugzilla_ids: Optional[list[int]] = None,
        alias: Optional[str] = None,
    ) -> Optional[tuple[str, str]]:
        """
        Create bodhi update.

        Args:
            dist_git_branch: Git reference.
            update_type: Type of the update, check CLI.
            update_notes: Notes about the update to be displayed in Bodhi. If not specified,
              automatic update notes including a changelog diff since the latest stable build
              will be generated.
            koji_builds: List of Koji builds or `None` (picks latest).
            sidetag: Koji sidetag to create the update from.
            bugzilla_ids: List of Bugzillas that are resolved with the update.
            alias: Alias of an existing update to edit. If not specified,
              a new update will be created.

        Returns:
            Alias and URL of the update or None if the update was already created.
        """
        logger.debug(
            f"Create bodhi update, "
            f"builds={koji_builds}, dg_branch={dist_git_branch}, type={update_type}"
            + (f", sidetag={sidetag}" if sidetag else ""),
        )
        return self.dg.create_bodhi_update(
            koji_builds=koji_builds,
            sidetag=sidetag,
            dist_git_branch=dist_git_branch,
            update_notes=update_notes,
            update_type=update_type,
            bugzilla_ids=bugzilla_ids,
            alias=alias,
        )

    def prepare_sources(
        self,
        upstream_ref: Optional[str] = None,
        update_release: Optional[bool] = None,
        release_suffix: Optional[str] = None,
        result_dir: Optional[Union[Path, str]] = None,
        create_symlinks: Optional[bool] = True,
        merged_ref: Optional[str] = None,
    ) -> None:
        """
        Prepare sources for an SRPM build.

        Args:
            upstream_ref: git ref to upstream commit used in source-git
            release_suffix: specifies local release suffix. `None` represents default suffix.
            update_release: whether to change Release in the spec-file
            result_dir: directory where the specfile directory content should be copied
            create_symlinks: whether symlinks should be created instead of copying the files
                (currently when the archive is created outside the specfile dir, or in the future
                 if we will create symlinks in some other places)
            merged_ref: git ref in the upstream repo used to identify correct most recent tag
        """
        self.up.actions_handler.run_action(
            actions=ActionName.post_upstream_clone,
            env=self.common_env(),
        )

        # reload spec file as it could have been changed by the action
        self.up.specfile.reload()

        if update_release is None:
            update_release = self.package_config.update_release
        try:
            self.up.prepare_upstream_for_srpm_creation(
                upstream_ref=upstream_ref,
                update_release=update_release,
                release_suffix=release_suffix,
                create_symlinks=create_symlinks,
                merged_ref=merged_ref,
                env=self.common_env(),
            )
        except Exception as ex:
            raise PackitSRPMException(
                f"Preparation of the repository for creation of an SRPM failed: {ex}",
            ) from ex

        if result_dir:
            self.copy_sources(result_dir)

        logger.info(
            f"Directory with sources: {result_dir or self.up.absolute_specfile_dir}",
        )

    def copy_sources(self, result_dir) -> None:
        """
        Copy content of the specfile directory to the `result_dir`.

        Args:
            result_dir: directory where the specfile directory content should be copied
        """
        logger.debug(f"Copying {self.up.absolute_specfile_dir} -> {result_dir}")
        copy_tree(
            str(self.up.absolute_specfile_dir),
            str(result_dir),
            preserve_symlinks=True,
        )

    def create_srpm(
        self,
        output_file: Optional[str] = None,
        upstream_ref: Optional[str] = None,
        srpm_dir: Optional[Union[Path, str]] = None,
        update_release: Optional[bool] = None,
        release_suffix: Optional[str] = None,
        merged_ref: Optional[str] = None,
    ) -> Path:
        """
        Create srpm from the upstream repo

        Args:
            upstream_ref: git ref to upstream commit
            output_file: path + filename where the srpm should be written, defaults to cwd
            srpm_dir: path to the directory where the srpm is meant to be placed
            release_suffix: specifies local release suffix. `None` represents default suffix.
            update_release: whether to change Release in the spec-file
            merged_ref: git ref in the upstream repo used to identify correct most recent tag

        Returns:
            a path to the srpm
        """
        try:
            self.prepare_sources(
                upstream_ref,
                update_release,
                release_suffix,
                merged_ref=merged_ref,
            )
            try:
                srpm_path = self.up.create_srpm(
                    srpm_path=output_file,
                    srpm_dir=srpm_dir,
                )
            except PackitSRPMException:
                raise
            except Exception as ex:
                raise PackitSRPMException(
                    f"An unexpected error occurred when creating the SRPM: {ex}",
                ) from ex

            if not srpm_path.exists():
                raise PackitSRPMNotFoundException(
                    f"SRPM was created successfully, but can't be found at {srpm_path}",
                )
            return srpm_path
        finally:
            self.clean()

    def create_rpms(
        self,
        upstream_ref: Optional[str] = None,
        rpm_dir: Optional[str] = None,
        release_suffix: Optional[str] = None,
        merged_ref: Optional[str] = None,
    ) -> list[Path]:
        """
        Create RPMs from the upstream repository.

        Args:
            upstream_ref: Git reference to the upstream commit.
            rpm_dir: Path to the directory where the RPMs are meant to be placed.
            release_suffix: Release suffix that is used during modification of specfile.
            merged_ref: git ref in the upstream repo used to identify correct most recent tag

        Returns:
            List of paths to the built RPMs.
        """
        self.up.actions_handler.run_action(
            actions=ActionName.post_upstream_clone,
            env=self.common_env(),
        )

        # reload spec file as it could have been changed by the action
        self.up.specfile.reload()

        try:
            self.up.prepare_upstream_for_srpm_creation(
                upstream_ref=upstream_ref,
                release_suffix=release_suffix,
                merged_ref=merged_ref,
                env=self.common_env(),
            )
        except Exception as ex:
            raise PackitRPMException(
                f"Preparing of the upstream to the RPM build failed: {ex}",
            ) from ex

        try:
            rpm_paths = self.up.create_rpms(rpm_dir=rpm_dir)
        except PackitRPMException:
            raise
        except Exception as ex:
            raise PackitRPMException(
                f"An unexpected error occurred when creating the RPMs: {ex}",
            ) from ex

        for rpm_path in rpm_paths:
            if not rpm_path.exists():
                raise PackitRPMNotFoundException(
                    f"RPM was created successfully, but can't be found at {rpm_path}",
                )
        return rpm_paths

    @staticmethod
    async def status_get_downstream_prs(status) -> list[tuple[int, str, str]]:
        try:
            await asyncio.sleep(0)
            return status.get_downstream_prs()
        except Exception as exc:
            # https://github.com/packit/ogr/issues/67 work-around
            logger.debug(f"Failed when getting downstream PRs: {exc}")
            return []

    @staticmethod
    async def status_get_dg_versions(status) -> dict:
        try:
            await asyncio.sleep(0)
            return status.get_dg_versions()
        except Exception as exc:
            logger.debug(f"Failed when getting Dist-git versions: {exc}")
            return {}

    @staticmethod
    async def status_get_up_releases(status) -> list:
        try:
            await asyncio.sleep(0)
            return status.get_up_releases()
        except Exception as exc:
            logger.debug(f"Failed when getting upstream releases: {exc}")
            return []

    @staticmethod
    async def status_get_koji_builds(status) -> dict:
        try:
            await asyncio.sleep(0)
            return status.get_koji_builds()
        except Exception as exc:
            logger.debug(f"Failed when getting Koji builds: {exc}")
            return {}

    @staticmethod
    async def status_get_copr_builds(status) -> list:
        try:
            await asyncio.sleep(0)
            return status.get_copr_builds()
        except Exception as exc:
            logger.debug(f"Failed when getting Copr builds: {exc}")
            return []

    @staticmethod
    async def status_get_updates(status) -> list:
        try:
            await asyncio.sleep(0)
            return status.get_updates()
        except Exception as exc:
            logger.debug(f"Failed when getting Bodhi updates: {exc}")
            return []

    @staticmethod
    async def status_main(status: Status) -> list:
        """
        Schedule repository data retrieval calls concurrently.
        :param status: status of the package
        :return: awaitable tasks
        """
        return await asyncio.gather(
            PackitAPI.status_get_downstream_prs(status),
            PackitAPI.status_get_dg_versions(status),
            PackitAPI.status_get_up_releases(status),
            PackitAPI.status_get_koji_builds(status),
            PackitAPI.status_get_copr_builds(status),
            PackitAPI.status_get_updates(status),
        )

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
                tabulate(copr_builds, headers=["Build ID", "Project name", "Status"]),
            )
        else:
            click.echo("\nNo Copr builds found.")

    def run_copr_build(
        self,
        project: str,
        chroots: list[str],
        owner: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        upstream_ref: Optional[str] = None,
        list_on_homepage: bool = False,
        preserve_project: bool = False,
        additional_packages: Optional[list[str]] = None,
        additional_repos: Optional[list[str]] = None,
        bootstrap: Optional[MockBootstrapSetup] = None,
        request_admin_if_needed: bool = False,
        enable_net: bool = False,
        release_suffix: Optional[str] = None,
        srpm_path: Optional[Path] = None,
        module_hotfixes: bool = False,
        follow_fedora_branching: bool = False,
    ) -> tuple[int, str]:
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
            bootstrap: mock bootstrap feature setup.
            request_admin_if_needed: Specifies whether to ask for admin privileges,
                if changes to configuration of Copr project are required.
            enable_net: Specifies whether created Copr build should have access
                to network during its build.
            release_suffix: Release suffix that is used during generation of SRPM.
            srpm_path: Specifies the path to the prebuilt SRPM. It is preferred
                to the implicit creation of the SRPM.
            module_hotfixes: Specifies whether copr should make packages from this
                project available along with packages from the active module streams.
            follow_fedora_branching: If newly branched chroots should be
                automatically enabled and populated.

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
                "Copr owner not set. Use Copr config file or `--owner` when calling packit CLI.",
            )
        logger.info(f"We will operate with COPR owner {owner}.")

        self.copr_helper.create_or_update_copr_project(
            project=project,
            chroots=chroots,
            owner=owner,
            description=description,
            instructions=instructions,
            list_on_homepage=list_on_homepage,
            preserve_project=preserve_project,
            additional_packages=additional_packages,
            additional_repos=additional_repos,
            bootstrap=bootstrap,
            request_admin_if_needed=request_admin_if_needed,
            module_hotfixes=module_hotfixes,
            follow_fedora_branching=follow_fedora_branching,
        )
        logger.debug(
            f"Submitting a build to copr build system,"
            f"owner={owner}, project={project}, path={srpm_path}",
        )

        build = self.copr_helper.copr_client.build_proxy.create_from_file(
            ownername=owner,
            projectname=project,
            path=srpm_path,
            buildopts={"enable_net": enable_net},
        )
        return build.id, self.copr_helper.copr_web_build_url(build)

    def watch_copr_build(
        self,
        build_id: int,
        timeout: int,
        report_func: Optional[Callable] = None,
    ) -> str:
        """returns copr build state"""
        return self.copr_helper.watch_copr_build(
            build_id=build_id,
            timeout=timeout,
            report_func=report_func,
        )

    def run_osh_build(
        self,
        chroot: Optional[str] = "fedora-rawhide-x86_64",
        srpm_path: Optional[Path] = None,
        upstream_ref: Optional[str] = None,
        release_suffix: Optional[str] = None,
        base_srpm: Optional[Path] = None,
        base_nvr: Optional[str] = None,
        comment: Optional[str] = "Submitted through Packit.",
        csmock_args: Optional[str] = None,
    ) -> str:
        """
        Perform a build through OpenScanHub.
        """

        if base_srpm and base_nvr:
            logger.error(
                "Either base SRPM or NVR can be specified for differential scans but not both",
            )
            return None

        # `osh-cli` requires a kerberos ticket.
        self.init_kerberos_ticket()

        if not srpm_path:
            srpm_path = self.create_srpm(
                upstream_ref=upstream_ref,
                srpm_dir=self.up.local_project.working_dir,
                release_suffix=release_suffix,
            )

        if base_srpm:
            cmd = [
                "osh-cli",
                "version-diff-build",
                "--srpm=" + str(srpm_path),
                "--base-srpm=" + str(base_srpm),
            ]
        elif base_nvr:
            cmd = [
                "osh-cli",
                "version-diff-build",
                "--srpm=" + str(srpm_path),
                "--base-nvr=" + base_nvr,
            ]
        else:
            cmd = ["osh-cli", "mock-build", str(srpm_path)]

        if csmock_args is None:
            csmock_args = self.package_config.csmock_args

        if csmock_args:
            cmd.append("--csmock-args=" + shlex.quote(csmock_args))

        osh_config = str(chroot)

        if osh_options := self.package_config.osh_options:
            if analyzer := osh_options.analyzer:
                cmd.append("--analyzer=" + shlex.quote(analyzer))
            if profile := osh_options.profile:
                cmd.append("--profile=" + shlex.quote(profile))
            if config := osh_options.config:
                osh_config = shlex.quote(config)

        cmd.append("--config=" + osh_config)
        cmd.append("--nowait")
        cmd.append("--json")
        cmd.append("--comment=" + comment)

        logger.info(f"Full command passed to osh-cli -> {cmd}")

        try:
            cmd_result = commands.run_command(cmd, output=True)
        except PackitCommandFailedError as ex:
            logger.error(ex.stderr_output)
            return None

        return cmd_result.stdout

    def run_obs_build(
        self,
        build_dir: str,
        package_name: str,
        project_name: str,
        upstream_ref: Optional[str],
        wait: bool = False,
    ):
        """
        Commit a build to the Open Build Service
        """

        # Initialise project directory
        package_dir = obs_helper.init_obs_project(
            build_dir,
            package_name,
            project_name,
        )
        logger.info(f"build: dir: {build_dir}")
        srpm = self.create_srpm(upstream_ref=upstream_ref, release_suffix="0")

        # Commit srpm to OBS
        obs_helper.commit_srpm_and_get_build_results(
            srpm,
            project_name,
            package_name,
            package_dir,
            upstream_ref,
            wait,
        )

    def push_bodhi_update(self, update_alias: str):
        """Push selected bodhi update from testing to stable."""
        from bodhi.client.bindings import UpdateNotFound

        bodhi_client = get_bodhi_client()
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
                f"- notes:\n{response['notes']}\n",
            )
        except UpdateNotFound:
            logger.error("Update was not found.")

    def get_testing_updates(self, update_alias: Optional[str]) -> list:
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
                update["date_testing"],
                "%Y-%m-%d %H:%M:%S",
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

        if self.pkg_tool.startswith("centpkg"):
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
        if self._up and self.up.local_project:
            self.up.local_project.free_resources()

    @staticmethod
    def validate_package_config(working_dir: Path, offline: bool = False) -> str:
        """Validate package config.

        Args:
            working_dir: Directory with the package config.

        Returns:
            String that the config is valid.

        Raises:
            PackitConfigException: when the config is not valid
        """

        config_path = find_packit_yaml(
            working_dir,
            try_local_dir_last=True,
        )
        config_content = load_packit_yaml(config_path)
        v = PackageConfigValidator(config_path, config_content, working_dir, offline)
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
        )
        sgg.create_from_upstream()

    def run_mock_build(
        self,
        srpm_path: Path,
        root: str = "default",
        resultdir: Union[Path, str, None] = None,
    ) -> list[Path]:
        """
        Performs a mock build with given SRPM and root.

        Args:
            root: Name of the chroot or path to the mock config.

                Defaults to `"default"` mock config which should be a Fedora
                rawhide.
            srpm_path: Path to the SRPM to be built.
            resultdir: Path where the mock results should be stored, for details
                see mock(1).

        Returns:
            List of paths to the built RPMs.
        """
        cmd = ["mock", "--root", root]
        if resultdir is not None:
            cmd.append("--resultdir")
            cmd.append(str(resultdir))

        cmd.append(str(srpm_path))
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
                f"{ex.stderr_output}",
            ) from ex
        except PackitException as ex:
            logger.error(f"The `mock` command failed: {ex!r}")
            raise PackitFailedToCreateRPMException(
                f"The `mock` command failed:\n{ex}",
            ) from ex

        rpms = GitUpstream._get_rpms_from_mock_output(cmd_result.stderr)
        return [Path(rpm) for rpm in rpms]

    def submit_vm_image_build(
        self,
        image_distribution: str,
        image_name: str,
        image_request: dict,
        image_customizations: dict,
        copr_namespace: Optional[str] = None,
        copr_project: Optional[str] = None,
        copr_chroot: Optional[str] = None,
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
        repo_url = (
            self.copr_helper.get_repo_download_url(
                owner=copr_namespace,
                project=copr_project,
                chroot=copr_chroot,
            )
            if copr_project is not None
            else None
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
