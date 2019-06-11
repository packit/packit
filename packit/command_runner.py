import logging
from typing import Dict, Type, List

from packit import utils
from packit.config import RunCommandType
from packit.local_project import LocalProject


logger = logging.getLogger(__name__)


RUN_COMMAND_HANDLER_MAPPING: Dict[RunCommandType, Type["RunCommandHandler"]] = {}


def add_run_command(kls: Type["RunCommandHandler"]):
    RUN_COMMAND_HANDLER_MAPPING[kls.name] = kls
    return kls


class RunCommandHandler:
    """Generic interface to handle different run_commands"""

    name: RunCommandType

    def __init__(
        self,
        local_project: LocalProject = None,
        cwd: str = None,
        output: bool = True,
        sandcastle_object=None,
    ):
        self.local_project = local_project
        self.cwd = cwd
        self.output = output
        self.sandcastle_object = sandcastle_object

    def run_command(self, command: List[str]):
        raise NotImplementedError("This should be implemented")


@add_run_command
class LocalRunCommandHandler(RunCommandHandler):
    name = RunCommandType.local

    def run_command(self, command: List[str]):
        """
        Executes command in current working directory
        :param command: command to execute
        This is not valid for this use case
        :return: Output of command
        """
        return utils.run_command(cmd=command, cwd=self.cwd, output=self.output)


@add_run_command
class SandcastleRunCommandHandler(RunCommandHandler):
    name = RunCommandType.sandcastle

    # TODO rename it to
    # from sandcastle.api import Sandcastle
    # as https://github.com/packit-service/sandcastle/pull/9
    # is merged
    from generator.deploy_openshift_pod import OpenshiftDeployer

    def run_command(self, command: List[str]):
        """
        Executes command in VolumeMount directory
        :param command: command to execute
        :return: Output of command from sandcastle_object
        """
        if not self.sandcastle_object.is_pod_already_deployed():
            self.sandcastle_object.run()
        return self.sandcastle_object.exec(command=command)
