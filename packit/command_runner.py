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
        self, local_project: LocalProject = None, cwd: str = None, output: bool = True
    ):
        self.local_project = local_project
        self.cwd = cwd
        self.output = output

    def run_command(self, command: List[str], openshift_deployer=None):
        raise NotImplementedError("This should be implemented")


@add_run_command
class CLIRunCommandHandler(RunCommandHandler):
    name = RunCommandType.cli

    def run_command(self, command: List[str], openshift_deployer=None):
        """
        Executes command in current working directory
        :param command: command to execute
        :param openshift_deployer: reference to Openshift Deployer class.
        This is not valid for this use case
        :return:
        """
        return utils.run_command(cmd=command, cwd=self.cwd, output=self.output)


@add_run_command
class OpenShiftRunCommandHandler(RunCommandHandler):
    name = RunCommandType.openshift

    from generator.deploy_openshift_pod import OpenshiftDeployer

    def run_command(
        self, command: List[str], openshift_deployer: OpenshiftDeployer = None
    ):
        """
        Executes command in VolumeMount directory
        :param command: command to execute
        :param cwd: Mount directory in OpenShift
        :param output: Print command output
        :return:
        """
        return openshift_deployer.exec(command=command)
