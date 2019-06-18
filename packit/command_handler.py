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

    def run_command(self, command: List[str], return_output=True):
        raise NotImplementedError("This should be implemented")

    def clean(self):
        """ clean up the mess after we're done """
        logger.info("nothing to clean")


@add_run_command
class LocalCommandHandler(CommandHandler):
    name = RunCommandType.local

    def run_command(self, command: List[str], return_output=True):
        """
        :param command: command to execute
        :param return_output: return output of the command if True
        """
        return utils.run_command(
            cmd=command, cwd=self.local_project.working_dir, output=return_output
        )


@add_run_command
class SandcastleCommandHandler(CommandHandler):
    name = RunCommandType.sandcastle

    def __init__(self, local_project: LocalProject, config: Config):
        """
        :param local_project:
        :param config:
        """
        # we import here so that packit does not depend on sandcastle (and thus python-kube)
        from sandcastle.api import Sandcastle, VolumeSpec

        super().__init__(local_project, config)
        v = VolumeSpec(
            path=local_project.working_dir,
            pvc_from_env=config.command_handler_pvc_env_var,
        )
        self.sandcastle = Sandcastle(
            image_reference=config.command_handler_image_reference,
            k8s_namespace_name=config.command_handler_k8s_namespace,
            working_dir=config.command_handler_work_dir,
            volume_mounts=[v],
        )

    def run_command(self, command: List[str], return_output=True) -> Optional[str]:
        """
        Executes command in a sandbox provided by sandcastle.

        :param command: command to execute
        :param return_output: return the output as str if True
        """
        if not self.sandcastle.is_pod_already_deployed():
            self.sandcastle.run()
        out = self.sandcastle.exec(command=command)
        if return_output:
            return out
        return None

    def clean(self):
        logger.info("removing sandbox pod")
        self.sandcastle.delete_pod()
