import logging
from typing import Dict, Type, List

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

    def run_command(self, command: List[str], return_output: bool = True):
        """
        exec a command

        :param command: the command
        :param return_output: return output from this method if True
        """
        raise NotImplementedError("This should be implemented")

    def clean(self):
        """ clean up the mess after we're done """
        logger.info("nothing to clean")


@add_run_command
class LocalCommandHandler(CommandHandler):
    name = RunCommandType.local

    def run_command(self, command: List[str], return_output=True):
        """
        exec a command

        :param command: the command
        :param return_output: return output from this method if True
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
        from sandcastle.api import Sandcastle, MappedDir

        super().__init__(local_project, config)
        md = MappedDir(
            local_dir=local_project.working_dir,
            path=config.command_handler_work_dir,
            with_interim_pvc=True,
        )
        self.sandcastle = Sandcastle(
            image_reference=config.command_handler_image_reference,
            k8s_namespace_name=config.command_handler_k8s_namespace,
            mapped_dir=md,
        )

    def run_command(self, command: List[str], return_output=True):
        """
        Executes command in a sandbox provided by sandcastle.

        :param command: the command
        :param return_output: return output from this method if True
        """
        if not self.sandcastle.is_pod_already_deployed():
            self.sandcastle.run()
        logger.info("running command: %s", command)
        out = self.sandcastle.exec(command=command)
        if return_output:
            return out
        return None

    def clean(self):
        logger.info("removing sandbox pod")
        self.sandcastle.delete_pod()
