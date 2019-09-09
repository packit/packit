import logging
from typing import Dict, Type, List, Optional

from packit import utils
from packit.config import RunCommandType, Config
from packit.local_project import LocalProject

logger = logging.getLogger(__name__)


RUN_COMMAND_HANDLER_MAPPING: Dict[RunCommandType, Type["CommandHandler"]] = {}


def add_run_command(kls: Type["CommandHandler"]):
    RUN_COMMAND_HANDLER_MAPPING[kls.name] = kls
    return kls


class CommandHandler:
    """Generic interface to handle different run_commands"""

    name: RunCommandType

    def __init__(self, local_project: LocalProject, config: Config):
        """

        :param local_project:
        :param config:
        """
        self.local_project = local_project
        self.config = config

    def run_command(
        self, command: List[str], return_output: bool = True, env: Optional[Dict] = None
    ):
        """
        exec a command

        :param command: the command
        :param return_output: return output from this method if True
        :param env: dict with env vars to set for the command
        """
        raise NotImplementedError("This should be implemented")

    def clean(self):
        """ clean up the mess after we're done """
        logger.info("nothing to clean")


@add_run_command
class LocalCommandHandler(CommandHandler):
    name = RunCommandType.local

    def run_command(
        self, command: List[str], return_output: bool = True, env: Optional[Dict] = None
    ):
        """
        exec a command

        :param command: the command
        :param return_output: return output from this method if True
        :param env: dict with env vars to set for the command
        """
        return utils.run_command(
            cmd=command,
            cwd=self.local_project.working_dir,
            output=return_output,
            env=env,
        )


@add_run_command
class SandcastleCommandHandler(CommandHandler):
    name = RunCommandType.sandcastle

    def run_command(
        self, command: List[str], return_output: bool = True, env: Optional[Dict] = None
    ):
        """
        Executes command in a sandbox provided by sandcastle.

        :param command: the command
        :param return_output: return output from this method if True
        :param env: dict with env vars to set for the command
        """
        # we import here so that packit does not depend on sandcastle (and thus python-kube)
        from sandcastle.api import Sandcastle, MappedDir

        md = MappedDir(
            local_dir=self.local_project.working_dir,
            path=self.config.command_handler_work_dir,
            with_interim_pvc=True,
        )
        sandcastle = Sandcastle(
            image_reference=self.config.command_handler_image_reference,
            k8s_namespace_name=self.config.command_handler_k8s_namespace,
            mapped_dir=md,
            env_vars=env,
        )
        sandcastle.run()
        try:
            logger.info("running command: %s", command)
            out = sandcastle.exec(command=command)
            if return_output:
                return out
            return None
        finally:
            sandcastle.delete_pod()
