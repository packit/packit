import logging
from typing import Callable

from packit import utils
from packit.actions import ActionName
from packit.utils import run_command
from packit.config import Config, PackageConfig
from packit.local_project import LocalProject

logger = logging.getLogger(__name__)


class CommandRunner:
    # mypy complains when this is a property
    local_project: LocalProject

    def __init__(
        self, config: Config, package_config: PackageConfig, local_project: LocalProject
    ):
        self.config = config
        self.package_config = package_config
        self.local_project = local_project

    def run_action(self, action: ActionName, method: Callable = None, *args, **kwargs):
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

        :param action: ActionName enum (Name of the action that can be overwritten
                                                in the package_config.actions)
        :param method: method to run if the action was not defined by user
                    (if not specified, the action can be used for custom hooks)
        :param args: args for the method
        :param kwargs: kwargs for the method
        """
        if not method:
            logger.debug(f"Running {action} hook.")
        if self.with_action(action=action):
            if method:
                method(*args, **kwargs)

    def has_action(self, action: ActionName) -> bool:
        """
        Is the action defined in the config?
        """
        return action in self.package_config.actions

    def with_action(self, action: ActionName) -> bool:
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
        :return: True, if the action is not overwritten, False when custom command was run
        """
        logger.debug(f"Running {action}.")
        if action in self.package_config.actions:
            command = self.package_config.actions[action]
            logger.info(f"Using user-defined script for {action}: {command}")
            utils.run_command(cmd=command, cwd=self.local_project.working_dir)
            return False
        logger.debug(f"Running default implementation for {action}.")
        return True

    def get_output_from_action(self, action: ActionName):
        """
        Run action if specified in the self.actions and return output
        else return None
        """
        if action in self.package_config.actions:
            command = self.package_config.actions[action]
            logger.info(f"Using user-defined script for {action}: {command}")
            return run_command(cmd=command, output=True)
        return None
