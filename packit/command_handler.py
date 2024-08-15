# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import tempfile
from os import getenv
from pathlib import Path
from typing import Optional, Union

from packit.config import Config, RunCommandType
from packit.local_project import LocalProject
from packit.utils import commands

logger = logging.getLogger(__name__)

RUN_COMMAND_HANDLER_MAPPING: dict[RunCommandType, type["CommandHandler"]] = {}


def add_run_command(kls: type["CommandHandler"]):
    RUN_COMMAND_HANDLER_MAPPING[kls.name] = kls
    return kls


class CommandHandler:
    """Generic interface to handle different run_commands"""

    name: RunCommandType

    def __init__(
        self,
        config: Config,
        local_project: Optional[LocalProject] = None,
        working_dir: Optional[Path] = None,
    ):
        self.local_project = local_project
        self.config = config
        self._working_dir = working_dir

    @property
    def working_dir(self) -> Union[str, Path]:
        if self.local_project:
            return self.local_project.working_dir

        if self._working_dir:
            return self._working_dir

        return tempfile.mkdtemp()

    def run_command(
        self,
        command: list[str],
        return_output: bool = True,
        env: Optional[dict] = None,
        cwd: Union[str, Path, None] = None,
        print_live: bool = False,
    ) -> commands.CommandResult:
        """
        Run provided command in a new subprocess.

        Args:
            command: Command to be run.
            return_output: Return the output of the subprocess.

                Defaults to `False`.
            env: Environment variables to be set in the newly created subprocess.

                Defaults to none.
            cwd: Working directory of the new subprocess.

                Defaults to current working directory of the process itself.
            print_live: Print real-time output of the command as INFO.

                Defaults to `False`.

        Returns:
            In case `output = False`, returns boolean that indicates success of
            the command that was run.

            Otherwise returns pair of `stdout` and `stderr` produced by the
            subprocess. It can be pair of bytes or string, depending on the value
            of `decode` parameter.
        """
        raise NotImplementedError("This should be implemented")

    def clean(self) -> None:
        """clean up the mess after we're done"""
        logger.info("Nothing to clean.")


@add_run_command
class LocalCommandHandler(CommandHandler):
    """
    Local command handler that runs commands locally without any sandboxing.
    """

    name = RunCommandType.local

    def run_command(
        self,
        command: list[str],
        return_output: bool = True,
        env: Optional[dict] = None,
        cwd: Union[str, Path, None] = None,
        print_live: bool = False,
    ) -> commands.CommandResult:
        return commands.run_command(
            cmd=command,
            cwd=cwd or self.working_dir,
            output=return_output,
            env=env,
            print_live=print_live,
        )


@add_run_command
class SandcastleCommandHandler(CommandHandler):
    """
    Sandcastle command handler that runs commands in a sandbox provided by
    a Sandcastle.

    Warning: `.success` on returned `CommandResult` is set to `False`, since
    only logs are fetched from the Sandcastle pods.
    """

    name = RunCommandType.sandcastle

    def __init__(
        self,
        config: Config,
        local_project: Optional[LocalProject] = None,
        working_dir: Optional[Path] = None,
    ):
        super().__init__(
            local_project=local_project,
            config=config,
            working_dir=working_dir,
        )
        self.local_project = local_project
        self.config = config
        # we import here so that packit does not depend on sandcastle (and thus python-kube)
        from sandcastle.api import MappedDir, Sandcastle

        self._sandcastle: Optional[Sandcastle] = None
        self._mapped_dir: Optional[MappedDir] = None

    @property
    def sandcastle(self):
        """initialize Sandcastle lazily"""
        if self._sandcastle is None:
            # we import here so that packit does not depend on sandcastle (and thus python-kube)
            from sandcastle.api import MappedDir, Sandcastle, VolumeSpec

            self._mapped_dir = MappedDir(
                local_dir=self.config.command_handler_work_dir,  # path on worker
                path=self.config.command_handler_work_dir,  # path on sandcastle, it's the same!
                with_interim_pvc=True,
            )

            pvc_volume_specs = [
                VolumeSpec(**vol_spec_dict)
                for vol_spec_dict in self.config.command_handler_pvc_volume_specs
                if (
                    # Do not mount when the env-var is not set
                    "pvc_from_env" not in vol_spec_dict
                    or getenv(vol_spec_dict.get("pvc_from_env"))
                )
                and not (
                    # Do not mount repository cache when it's not used
                    self.config.repository_cache
                    and vol_spec_dict.get("path") == self.config.repository_cache
                    and not (
                        self.local_project
                        and self.local_project.cache.projects_cloned_using_cache
                    )
                )
            ]

            self._sandcastle = Sandcastle(
                image_reference=self.config.command_handler_image_reference,
                k8s_namespace_name=self.config.command_handler_k8s_namespace,
                mapped_dir=self._mapped_dir,
                volume_mounts=pvc_volume_specs,
                storage_class=self.config.command_handler_storage_class,
                appcode=self.config.appcode,
            )
            logger.debug("running the sandcastle pod")
            self._sandcastle.run()
        return self._sandcastle

    @staticmethod
    def _print_logs(logs: str) -> None:
        """
        Print out logs line-by-line using logger with the INFO level.

        Args:
            logs: Logs gathered from the Sandcastle.
        """
        # out = 'make po-pull\nmake[1]: Entering directory \'/sand
        for output_line in logs.split("\n"):
            if output_line:
                logger.info(output_line)

    def run_command(
        self,
        command: list[str],
        return_output: bool = True,
        env: Optional[dict] = None,
        cwd: Union[str, Path, None] = None,
        print_live: bool = False,
    ) -> commands.CommandResult:
        from sandcastle.exceptions import SandcastleCommandFailed

        cwd = cwd or Path(self.working_dir).relative_to(
            self.config.command_handler_work_dir,
        )
        logger.info(f"Running command: {' '.join(command)} on dir {cwd}")

        out = ""
        try:
            out = self.sandcastle.exec(command=command, env=env, cwd=cwd)

            logger.info(f"Output of {command!r}:")
            self._print_logs(out)
        except SandcastleCommandFailed as ex:
            # TODO: Maybe consider logging as an error? Would spam Sentry though
            logger.info(f"Command {command!r} failed:")
            self._print_logs(ex.output)
            raise  # reraise the error to halt the execution of the job

        return commands.CommandResult(
            success=True,
            stdout=out if return_output else None,
        )

    def clean(self) -> None:
        if self._sandcastle:
            logger.info("Deleting sandcastle pod.")
            self._sandcastle.delete_pod()
            self._sandcastle = None
        else:
            logger.info("Sandcastle pod is not running, nothing to clean up")

    def __del__(self) -> None:
        self.clean()
