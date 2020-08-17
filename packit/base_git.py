# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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

import shlex
from logging import getLogger
from pathlib import Path
from typing import Optional, Callable, List, Iterable, Dict

import git
from git import PushInfo

from packit.actions import ActionName
from packit.command_handler import RUN_COMMAND_HANDLER_MAPPING, CommandHandler
from packit.config import Config, RunCommandType
from packit.config.common_package_config import CommonPackageConfig
from packit.exceptions import PackitException
from packit.local_project import LocalProject
from packit.patches import PatchMetadata
from packit.security import CommitVerifier
from packit.specfile import Specfile
from packit.utils.commands import cwd

logger = getLogger(__name__)


class PackitRepositoryBase:
    # mypy complains when this is a property
    local_project: LocalProject

    def __init__(self, config: Config, package_config: CommonPackageConfig) -> None:
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

    def running_in_service(self) -> bool:
        """ are we running in packit service? """
        return self.command_handler.name == RunCommandType.sandcastle

    @property
    def absolute_specfile_dir(self) -> Path:
        """ get dir where the spec file is"""
        return self.absolute_specfile_path.parent

    @property
    def absolute_specfile_path(self) -> Path:
        if not self._specfile_path:
            self._specfile_path = (
                self.local_project.working_dir / self.package_config.specfile_path
            )
            if not self._specfile_path.exists():
                raise FileNotFoundError(f"Specfile {self._specfile_path} not found.")

        return self._specfile_path

    @property
    def specfile(self) -> Specfile:
        if self._specfile is None:
            self._specfile = Specfile(
                self.absolute_specfile_path, self.absolute_specfile_dir
            )
        return self._specfile

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
        if branch_name in self.local_project.git_repo.branches:
            logger.debug(
                f"It seems that branch {branch_name!r} already exists, checking it out."
            )
            head = self.local_project.git_repo.branches[branch_name]
        else:
            head = self.local_project.git_repo.create_head(branch_name, commit=base)

        if setup_tracking:
            if branch_name in origin.refs:
                remote_ref = origin.refs[branch_name]
            else:
                raise PackitException(
                    f"Remote origin doesn't have ref {branch_name!r}."
                )
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
        if self.with_action(action=actions):
            if method:
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
                self.command_handler.run_command(command=cmd, env=env)
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

        outputs = []
        logger.info(f"Using user-defined script for {action}: {commands_to_run}")
        for cmd in commands_to_run:
            outputs.append(
                self.command_handler.run_command(cmd, return_output=True, env=env)
            )
        logger.debug(f"Action command output: {outputs}")
        return outputs

    def specfile_add_patches(self, patch_list: List[PatchMetadata]) -> None:
        """
        Add the given list of (patch_name, msg) to the specfile.

        :param patch_list: [PatchMetadata, ...]
        """
        if not patch_list:
            return

        self.specfile.remove_applied_patches()
        self.specfile.add_patches(patch_list)

        self.local_project.git_repo.index.write()

    def get_project_url_from_distgit_spec(self) -> Optional[str]:
        """
        Parse spec file and return value of URL
        """
        # consider using rebase-helper for this: SpecFile.download_remote_sources
        sections = self.specfile.spec_content.sections
        package_section: List[str] = sections.get("%package", [])
        for s in package_section:
            if s.startswith("URL:"):
                url = s[4:].strip()
                logger.debug(f"Upstream project URL: {url}")
                return url
        return None

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
            self.specfile.download_remote_sources()

    def set_specfile_content(self, specfile: Specfile, version: str, comment: str):
        """
        update this specfile using provided specfile

        :param specfile: specfile to get changes from (we update self.specfile)
        :param version: version to set in self.specfile
        :param comment: new comment for the version in %changelog
        """
        this_changelog = self.specfile.spec_content.section("%changelog")
        this_version = self.specfile.get_version()
        self.specfile.spec_content.sections[:] = specfile.spec_content.sections[:]
        self.specfile.save()
        self.specfile.spec_content.replace_section("%changelog", this_changelog)
        self.specfile.set_version(this_version)
        self.specfile.save()
        self.specfile.set_spec_version(version=version, changelog_entry=comment)

    def refresh_specfile(self):
        self._specfile = None

    def is_dirty(self) -> bool:
        """ is the git repo dirty? """
        return self.local_project.git_repo.is_dirty()

    def push(self, refspec: str, remote_name: str = "origin", force: bool = False):
        """ push selected refspec to a git remote """
        logger.info(
            f"Pushing changes to remote {remote_name!r} using refspec {refspec!r}."
        )
        push_infos_list: Iterable[PushInfo] = self.local_project.push(
            refspec, remote_name=remote_name, force=force
        )
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
