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

import logging
from pathlib import Path
from typing import Dict, Type, List, Optional, Union

from packit.utils import commands
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
        self,
        command: List[str],
        return_output: bool = True,
        env: Optional[Dict] = None,
        cwd: Union[str, Path] = None,
        print_live: bool = False,
    ):
        """
        exec a command

        :param command: the command
        :param return_output: return output from this method if True
        :param env: dict with env vars to set for the command
        :param cwd: working directory to run command in
        :param print_live: print output from the command realtime to INFO log
        """
        raise NotImplementedError("This should be implemented")

    def clean(self):
        """ clean up the mess after we're done """
        logger.info("Nothing to clean.")


@add_run_command
class LocalCommandHandler(CommandHandler):
    name = RunCommandType.local

    def run_command(
        self,
        command: List[str],
        return_output: bool = True,
        env: Optional[Dict] = None,
        cwd: Union[str, Path] = None,
        print_live: bool = False,
    ):
        """
        exec a command

        :param command: the command
        :param return_output: return output from this method if True
        :param env: dict with env vars to set for the command
        :param cwd: working directory to run command in
        :param print_live: print output from the command realtime to INFO log
        """
        return commands.run_command(
            cmd=command,
            cwd=cwd or self.local_project.working_dir,
            output=return_output,
            env=env,
            print_live=print_live,
        )


@add_run_command
class SandcastleCommandHandler(CommandHandler):
    name = RunCommandType.sandcastle

    def run_command(
        self,
        command: List[str],
        return_output: bool = True,
        env: Optional[Dict] = None,
        cwd: Union[str, Path] = None,
        print_live: bool = False,
    ):
        """
        Executes command in a sandbox provided by sandcastle.

        :param command: the command
        :param return_output: return output from this method if True
        :param env: dict with env vars to set for the command
        :param cwd: working directory to run command in
        :param print_live: not used here
        """
        # we import here so that packit does not depend on sandcastle (and thus python-kube)
        from sandcastle.api import Sandcastle, MappedDir

        md = MappedDir(
            local_dir=self.local_project.working_dir,
            path=cwd or self.config.command_handler_work_dir,
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
            logger.info(f"Running command: {' '.join(command)}")
            out: str = sandcastle.exec(command=command)
        finally:
            sandcastle.delete_pod()

        logger.info(f"Output of {command!r}:")
        # out = 'make po-pull\nmake[1]: Entering directory \'/sand
        for output_line in out.split("\n"):
            if output_line:
                logger.info(output_line)

        if return_output:
            return out
        return None
