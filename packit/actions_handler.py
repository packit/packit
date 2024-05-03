# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import shlex
from logging import getLogger
from typing import Callable, Optional

from packit.actions import ActionName
from packit.command_handler import CommandHandler
from packit.config import MultiplePackages

logger = getLogger(__name__)


class ActionsHandler:
    def __init__(
        self,
        package_config: MultiplePackages,
        command_handler: CommandHandler,
    ):
        self.package_config = package_config
        self.command_handler = command_handler

    def run_action(
        self,
        actions: ActionName,
        method: Optional[Callable] = None,
        env: Optional[dict] = None,
        *args,
        **kwargs,
    ):
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
        if self.with_action(action=actions, env=env) and method:
            method(*args, **kwargs)

    def has_action(self, action: ActionName) -> bool:
        """
        Is the action defined in the config?
        """
        return action in self.package_config.actions

    def get_commands_for_actions(self, action: ActionName) -> list[list[str]]:
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
                f"The value: {configured_action}",
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
                    f"The value: {cmd}",
                )
        return parsed_commands

    def with_action(self, action: ActionName, env: Optional[dict] = None) -> bool:
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
        self,
        action: ActionName,
        env: Optional[dict] = None,
    ) -> Optional[list[str]]:
        """
        Run self.actions[action] command(s) and return their outputs.
        """
        if action not in self.package_config.actions:
            return None

        commands_to_run = self.get_commands_for_actions(action)

        logger.info(f"Using user-defined script for {action}: {commands_to_run}")
        return [
            self.command_handler.run_command(
                cmd,
                return_output=True,
                env=env,
                print_live=True,
            ).stdout
            for cmd in commands_to_run
        ]
