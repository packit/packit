# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import shlex
from logging import getLogger
from pathlib import Path
from typing import Optional, Callable, List, Iterable, Dict, Tuple

import git
import requests
from git import PushInfo
from specfile import Specfile
from specfile.exceptions import DuplicateSourceException, SourceNumberException
from specfile.sections import Section

from ogr.abstract import PullRequest

from packit.actions import ActionName
from packit.command_handler import RUN_COMMAND_HANDLER_MAPPING, CommandHandler
from packit.config import Config, RunCommandType
from packit.config.common_package_config import MultiplePackages
from packit.exceptions import PackitException, PackitDownloadFailedException
from packit.local_project import LocalProject
from packit.patches import PatchMetadata
from packit.security import CommitVerifier
from packit.utils.commands import cwd
from packit.utils.lookaside import get_lookaside_sources
from packit.utils.repo import RepositoryCache, commit_message_file

logger = getLogger(__name__)


class PackitRepositoryBase:
    # mypy complains when this is a property
    local_project: LocalProject

    def __init__(
        self,
        config: Config,
        package_config: MultiplePackages,
    ) -> None:
        """
        :param config: global configuration
        :param package_config: configuration of the upstream project
        """
        self.config = config
        self.package_config = package_config
        self._specfile_path: Optional[Path] = None
        self._specfile: Optional[Specfile] = None
        self.allowed_gpg_keys: Optional[List[str]] = None

        self._handler_kls = None
        self._command_handler: Optional[CommandHandler] = None

    @property
    def handler_kls(self):
        if self._handler_kls is None:
            logger.debug(f"Command handler: {self.config.command_handler}")
            self._handler_kls = RUN_COMMAND_HANDLER_MAPPING[self.config.command_handler]
        return self._handler_kls

    @property
    def command_handler(self) -> CommandHandler:
        if self._command_handler is None:
            self._command_handler = self.handler_kls(
                local_project=self.local_project, config=self.config
            )
        return self._command_handler

    @property
    def repository_cache(self) -> Optional[RepositoryCache]:
        if self.config.repository_cache:
            return RepositoryCache(
                cache_path=self.config.repository_cache,
                add_new=self.config.add_repositories_to_repository_cache,
            )
        return None

    def is_command_handler_set(self) -> bool:
        """return True when command_handler is initialized"""
        return bool(self._command_handler)

    def running_in_service(self) -> bool:
        """are we running in packit service?"""
        return self.command_handler.name == RunCommandType.sandcastle

    @property
    def absolute_specfile_dir(self) -> Path:
        """get dir where the spec file is"""
        return self.absolute_specfile_path.parent

    def get_absolute_specfile_path(self) -> Path:
        return self.local_project.working_dir / self.package_config.specfile_path

    @property
    def absolute_specfile_path(self) -> Path:
        if not self._specfile_path:
            self._specfile_path = self.get_absolute_specfile_path()
            if not self._specfile_path.exists():
                # since propose-downstream checks out a tag, we should inform user
                # on which ref this has happened: https://github.com/packit/packit/issues/1625
                raise FileNotFoundError(
                    f"Specfile {self._specfile_path} not found on ref {self.local_project.ref}."
                )

        return self._specfile_path

    @property
    def specfile(self) -> Specfile:
        if self._specfile is None:
            self._specfile = Specfile(
                self.absolute_specfile_path,
                sourcedir=self.absolute_source_dir,
                autosave=True,
            )
        return self._specfile

    @property
    def absolute_source_dir(self) -> Path:
        """
        absolute path to the directory where `Source` files
        from spec files can be found
        """
        return self.absolute_specfile_dir

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
        # keeping the method in this class to preserve compatibility
        return self.local_project.create_branch(
            branch_name=branch_name, base=base, setup_tracking=setup_tracking
        )

    def checkout_branch(self, git_ref: str = None):
        """
        Perform a `git checkout`

        :param git_ref: ref to check out, defaults to repo's default branch
        """
        git_ref = git_ref or self.local_project.git_project.default_branch
        logger.debug(f"Checking out branch {git_ref}.")
        if git_ref in self.local_project.git_repo.heads:
            head = self.local_project.git_repo.heads[git_ref]
        else:
            raise PackitException(f"Branch {git_ref} does not exist")
        head.checkout()

    def commit(
        self,
        title: str,
        msg: str,
        prefix: str = "[packit] ",
        trailers: Optional[List[Tuple[str, str]]] = None,
    ) -> None:
        """
        Perform `git add -A` and `git commit`
        """
        logger.debug("About to add all & commit.")
        main_msg = f"{prefix}{title}"
        # add files to index in case some are untracked
        # untracked files don't make a git repo dirty, unless they are staged
        self.local_project.git_repo.git.add("-A")
        if not self.local_project.git_repo.is_dirty():
            raise PackitException(
                "No changes are present in the dist-git repo: nothing to commit."
            )
        self.local_project.git_repo.index.write()

        with commit_message_file(main_msg, msg, trailers) as commit_message:
            # TODO: make -s configurable
            commit_args = ["-s", "-F", commit_message]
            self.local_project.git_repo.git.commit(*commit_args)

    def run_action(self, actions: ActionName, method: Callable = None, *args, **kwargs):
        """
        Run the method in the self._with_action block.

        Usage:

        >   self._run_action(
        >        action_name="sync", method=dg.sync_files, upstream_project=up.local_project
        >   )
        >   # If user provided custom command for the `sync`, it will be used.
        >   # Otherwise, the method `dg.sync_files` will be used
        >   # with parameter `upstream_project=up.local_project`
        >
        >   self._run_action(action_name="pre-sync")
        >   # This will be used as an optional hook

        :param actions: ActionName enum (Name of the action that can be overwritten
                                                in the package_config.actions)
        :param method: method to run if the action was not defined by user
                    (if not specified, the action can be used for custom hooks)
        :param args: args for the method
        :param kwargs: kwargs for the method
        """
        if not method:
            logger.debug(f"Running {actions} hook.")
        if self.with_action(action=actions) and method:
            method(*args, **kwargs)

    def has_action(self, action: ActionName) -> bool:
        """
        Is the action defined in the config?
        """
        return action in self.package_config.actions

    def get_commands_for_actions(self, action: ActionName) -> List[List[str]]:
        """
        Parse the following types of the structure and return list of commands in the form of list.

        I)
        action_name: "one cmd"

        II)
        action_name:
          - "one cmd""

        III)
        action_name:
          - ["one", "cmd"]


        Returns [["one", "cmd"]] for all of them.

        :param action: str or list[str] or list[list[str]]
        :return: list[list[str]]
        """
        configured_action = self.package_config.actions[action]
        if isinstance(configured_action, str):
            configured_action = [configured_action]

        if not isinstance(configured_action, list):
            raise ValueError(
                f"Expecting 'str' or 'list' as a command, got '{type(configured_action)}'. "
                f"The value: {configured_action}"
            )

        parsed_commands = []
        for cmd in configured_action:
            if isinstance(cmd, str):
                parsed_commands.append(shlex.split(cmd))
            elif isinstance(cmd, list):
                parsed_commands.append(cmd)
            else:
                raise ValueError(
                    f"Expecting 'str' or 'list' as a command, got '{type(cmd)}'. "
                    f"The value: {cmd}"
                )
        return parsed_commands

    def with_action(self, action: ActionName, env: Optional[Dict] = None) -> bool:
        """
        If the action is defined in the self.package_config.actions,
        we run it and return False (so we can skip the if block)

        If the action is not defined, return True.

        Usage:

        >   if self._with_action(action_name="patch"):
        >       # Run default implementation
        >
        >   # Custom command was run if defined in the config

        Context manager is currently not possible without ugly hacks:
        https://stackoverflow.com/questions/12594148/skipping-execution-of-with-block
        https://www.python.org/dev/peps/pep-0377/ (rejected)

        :param action: ActionName enum (Name of the action that can be overwritten
                                                in the package_config.actions)
        :param env: dict with env vars to set for the command
        :return: True, if the action is not overwritten, False when custom command was run
        """
        logger.debug(f"Running {action}.")
        if action in self.package_config.actions:
            commands_to_run = self.get_commands_for_actions(action)
            logger.info(f"Using user-defined script for {action}: {commands_to_run}")
            for cmd in commands_to_run:
                self.command_handler.run_command(command=cmd, env=env, print_live=True)
            return False
        logger.debug(f"Running default implementation for {action}.")
        return True

    def get_output_from_action(
        self, action: ActionName, env: Optional[Dict] = None
    ) -> Optional[List[str]]:
        """
        Run self.actions[action] command(s) and return their outputs.
        """
        if action not in self.package_config.actions:
            return None

        commands_to_run = self.get_commands_for_actions(action)

        logger.info(f"Using user-defined script for {action}: {commands_to_run}")
        return [
            self.command_handler.run_command(
                cmd, return_output=True, env=env, print_live=True
            ).stdout
            for cmd in commands_to_run
        ]

    def specfile_add_patches(
        self, patch_list: List[PatchMetadata], patch_id_digits: int = 4
    ) -> None:
        """
        Add the given list of (patch_name, msg) to the specfile.

        :param patch_list: [PatchMetadata, ...]
        :param patch_id_digits: Number of digits of the generated patch ID.
            This is used to control whether to have 'Patch1' or 'Patch0001'.
        """
        if not patch_list:
            return

        if all(p.present_in_specfile for p in patch_list):
            logger.debug(
                "All patches are present in the spec file, nothing to do here 🚀"
            )
            return

        # we could have generated patches before (via git-format-patch)
        # so let's reload the spec
        self.specfile.reload()

        for patch_metadata in patch_list:
            if patch_metadata.present_in_specfile:
                logger.debug(
                    f"Patch {patch_metadata.name} is already present in the spec file."
                )
                continue

            try:
                logger.debug(f"Adding patch {patch_metadata.name} to the spec file.")
                self.specfile.add_patch(
                    patch_metadata.name,
                    patch_metadata.patch_id,
                    patch_metadata.specfile_comment,
                    initial_number=1,
                    number_digits=patch_id_digits,
                )
            except DuplicateSourceException:
                logger.debug(
                    f"Patch {patch_metadata.name} is already defined in the spec file."
                )
            except SourceNumberException as e:
                raise PackitException(
                    f"The 'patch_id' requested ({patch_metadata.patch_id}) for patch "
                    f"{patch_metadata.name} is less than or equal to the last used patch ID."
                    "Re-ordering the patches using 'patch_id' is not allowed - "
                    "if you want to change the order of those patches, "
                    "please reorder the commits in your source-git repository."
                ) from e

        self.local_project.git_repo.index.write()

    def check_last_commit(self) -> None:
        if self.allowed_gpg_keys is None:
            logger.debug("Allowed GPG keys are not set, skipping the verification.")
            return

        ver = CommitVerifier()
        last_commit = self.local_project.git_repo.head.commit
        valid = ver.check_signature_of_commit(
            commit=last_commit, possible_key_fingerprints=self.allowed_gpg_keys
        )
        if not valid:
            msg = f"Last commit {last_commit.hexsha!r} not signed by the authorized gpg key."
            logger.warning(msg)
            raise PackitException(msg)

    def fetch_upstream_archive(self):
        with cwd(self.absolute_specfile_dir):
            self.download_remote_sources()

    def set_specfile_content(
        self,
        specfile: Specfile,
        version: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        """
        Update the spec-file in this repository using the provided spec-file.

        1. The whole content of the spec-file is copied.
        2. The changelog is preserved.
        3. If provided, new version is set.
        4. If provided, new changelog entry is added.
        5. Release is reset to 1, if the version has changed and the release
           stayed the same.

        Args:
            specfile: specfile to get changes from (we update self.specfile)
            version: version to set in self.specfile
            comment: new comment for the version in %changelog
        """
        previous_release = self.specfile.release
        previous_version = self.specfile.expanded_version
        with self.specfile.sections() as sections, specfile.sections() as other_sections:
            try:
                previous_changelog = sections.changelog[:]
            except AttributeError:
                previous_changelog = []
            sections[:] = other_sections[:]
            try:
                sections.changelog = previous_changelog
            except AttributeError:
                sections.append(Section("changelog", previous_changelog))
        if version is not None:
            self.specfile.version = version
        if (
            previous_version != self.specfile.expanded_version
            and previous_release == self.specfile.release
        ):
            # This may occur if the upstream forgets to reset release after
            # bumping the version, or if the specfile is not maintained in
            # upstream at all (e.g. post-upstream-clone that uses wget to
            # get the specfile from Fedora).
            # Either way, it seems better to fix it at least in downstream
            # at the cost of upstream and downstream having different
            # Release fields.
            self.specfile.release = "1"
        if comment is not None:
            self.specfile.add_changelog_entry(comment)

    def refresh_specfile(self):
        self._specfile = None

    def set_specfile(self, specfile: Specfile):
        self._specfile = specfile

    def is_dirty(self) -> bool:
        """is the git repo dirty?"""
        return self.local_project.git_repo.is_dirty()

    def push(self, refspec: str, remote_name: str = "origin", force: bool = False):
        """push selected refspec to a git remote"""
        logger.info(
            f"Pushing changes to remote {remote_name!r} using refspec {refspec!r}."
        )
        push_infos_list: Iterable[PushInfo] = self.local_project.git_repo.remote(
            name=remote_name
        ).push(refspec=refspec, force=force)
        for pi in push_infos_list:
            logger.info(f"Push summary: {pi.summary}")
            push_failed = [
                bool(x & pi.flags)
                for x in (
                    PushInfo.ERROR,
                    PushInfo.REMOTE_FAILURE,
                    PushInfo.REMOTE_REJECTED,
                    PushInfo.NO_MATCH,  # this looks like it's not used in gitpython
                    PushInfo.REJECTED,
                    PushInfo.UP_TO_DATE,  # is this an error?
                )
            ]
            if any(push_failed):
                logger.debug(f"Push flags: {pi.flags}")
                raise PackitException(
                    f"We were unable to push to dist-git: {pi.summary}."
                )

    def download_remote_sources(self, pkg_tool: Optional[str] = None) -> None:
        """
        Download the sources from the URL in the configuration (if the path in
        the configuration match to the URL basename from SourceX) or from the one
        from SourceX in specfile.

        Args:
            pkg_tool: Packaging tool associated with a lookaside cache instance
              to be used for downloading sources.

        Raises:
            PackitDownloadFailedException if download fails for any reason.
        """
        sourcelist = []
        # Fetch all sources defined in packit.yaml -> sources
        for source in self.package_config.sources:
            sourcelist.append((source.url, source.path, False))
        if pkg_tool:
            # Fetch sources defined in "sources" file from lookaside cache
            lookaside_sources = get_lookaside_sources(
                pkg_tool,
                self.specfile.expanded_name,
                self.specfile.path.parent,
            )
            for lookaside_source in lookaside_sources:
                sourcelist.append(
                    (lookaside_source["url"], lookaside_source["path"], True)
                )
        # Fetch all remote sources defined in the spec file
        with self.specfile.sources() as sources, self.specfile.patches() as patches:
            for spec_source in sources + patches:
                if spec_source.remote:
                    sourcelist.append(
                        (
                            spec_source.expanded_location,
                            spec_source.expanded_filename,
                            False,
                        )
                    )
        # Download all sources
        for url, filename, optional in sourcelist:
            source_path = self.specfile.sourcedir.joinpath(filename)
            if source_path.is_file():
                continue
            try:
                with requests.get(url, stream=True) as response:
                    response.raise_for_status()
                    with open(source_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
            ) as e:
                msg = f"Failed to download source from {url}"
                if optional:
                    logger.warning(f"{msg}: {e!r}")
                    continue
                logger.error(f"{msg}: {e!r}")
                raise PackitDownloadFailedException(f"{msg}:\n{e}") from e

    def existing_pr(
        self, title: str, description: str, target_branch: str, source_branch: str
    ) -> Optional[PullRequest]:
        """Look for an already created PR with the same:
        title, description and branch name

        Args:
            title (str)
            description (str)
            branch (str)

        Return:
            PullRequest: if one is found otherwise None
        """
        pull_requests = self.local_project.git_project.get_pr_list()
        current_user = self.local_project.git_service.user.get_username()

        for pr in pull_requests:
            if (
                pr.title == title
                and pr.description == description
                and pr.target_branch == target_branch
                and pr.source_branch == source_branch
                and pr.author == current_user
            ):
                return pr
        return None
