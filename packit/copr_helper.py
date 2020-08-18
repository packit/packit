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
import time
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Dict, Tuple, Any

from copr.v3 import Client as CoprClient
from copr.v3.exceptions import (
    CoprNoResultException,
    CoprException,
    CoprRequestException,
)
from munch import Munch

from packit.constants import COPR2GITHUB_STATE
from packit.exceptions import PackitCoprProjectException, PackitCoprSettingsException
from packit.local_project import LocalProject

logger = logging.getLogger(__name__)


class CoprHelper:
    def __init__(self, upstream_local_project: LocalProject) -> None:
        self.upstream_local_project = upstream_local_project
        self._copr_client = None

    def __repr__(self):
        return (
            "CoprHelper("
            f"upstream_local_project='{self.upstream_local_project}', "
            f"copr_client='{self.copr_client}')"
        )

    def get_copr_client(self) -> CoprClient:
        """Not static because of the flex-mocking."""
        return CoprClient.create_from_config_file()

    @property
    def copr_client(self) -> CoprClient:
        if self._copr_client is None:
            self._copr_client = self.get_copr_client()
        return self._copr_client

    @property
    def configured_owner(self) -> Optional[str]:
        return self.copr_client.config.get("username")

    def copr_web_build_url(self, build: Munch) -> str:
        """ Construct web frontend url because build.repo_url is not much user-friendly."""
        copr_url = self.copr_client.config.get("copr_url")
        return f"{copr_url}/coprs/build/{build.id}/"

    def get_copr_settings_url(
        self, owner: str, project: str, section: Optional[str] = None
    ):
        copr_url = self.copr_client.config.get("copr_url")
        section = section or "edit"
        return f"{copr_url}/coprs/{owner}/{project}/{section}/"

    def create_copr_project_if_not_exists(
        self,
        project: str,
        chroots: List[str],
        owner: str = None,
        description: str = None,
        instructions: str = None,
        list_on_homepage: Optional[bool] = False,
        preserve_project: Optional[bool] = False,
        additional_packages: List[str] = None,
        additional_repos: List[str] = None,
        request_admin_if_needed: bool = False,
    ) -> None:
        """
        Create a project in copr if it does not exists.

        Raises PackitCoprException on any problems.
        """
        logger.info(
            f"Trying to get {owner}/{project} Copr project. "
            "The project will be created if it does not exist."
        )
        try:
            copr_proj = self.copr_client.project_proxy.get(
                ownername=owner, projectname=project
            )
        except CoprNoResultException as ex:
            if owner != self.configured_owner:
                raise PackitCoprProjectException(
                    f"Copr project {owner}/{project} not found."
                ) from ex

            logger.info(f"Copr project '{owner}/{project}' not found. Creating new.")
            self.create_copr_project(
                chroots=chroots,
                description=description,
                instructions=instructions,
                owner=owner,
                project=project,
                list_on_homepage=list_on_homepage,
                preserve_project=preserve_project,
                additional_packages=additional_packages,
                additional_repos=additional_repos,
            )
            return
        except CoprRequestException as ex:
            logger.debug(repr(ex))
            logger.error(
                f"We were not able to get copr project {owner}/{project}: {ex}"
            )
            raise

        delete_after_days: Optional[
            int
        ] = None if preserve_project is None else -1 if preserve_project else 60

        fields_to_change = self.get_fields_to_change(
            copr_proj=copr_proj,
            additional_repos=additional_repos,
            chroots=chroots,
            description=description,
            instructions=instructions,
            list_on_homepage=list_on_homepage,
            delete_after_days=delete_after_days,
        )

        if fields_to_change:
            logger.info(f"Updating copr project '{owner}/{project}'")
            for field, (old, new) in fields_to_change.items():
                logger.debug(f"{field}: {old} -> {new}")

            try:
                kwargs: Dict[str, Any] = {
                    arg_name: new for arg_name, (old, new) in fields_to_change.items()
                }
                logger.debug(f"Copr edit arguments: {kwargs}")
                self.copr_client.project_proxy.edit(
                    ownername=owner, projectname=project, **kwargs
                )
            except CoprRequestException as ex:
                if "Only owners and admins may update their projects." in str(ex):
                    if request_admin_if_needed:
                        logger.info(
                            f"Admin permissions are required "
                            f"in order to be able to edit project settings. "
                            f"Requesting the admin rights for the copr '{owner}/{project}' project."
                        )
                        self.copr_client.project_proxy.request_permissions(
                            ownername=owner,
                            projectname=project,
                            permissions={"admin": True},
                        )
                    else:
                        logger.warning(
                            f"Admin permissions are required for copr '{owner}/{project}' project"
                            f"in order to be able to edit project settings. "
                            f"You can make a request by specifying --request-admin-if-needed "
                            f"when using Packit CLI."
                        )
                raise PackitCoprSettingsException(
                    f"Copr project update failed for '{owner}/{project}' project.",
                    fields_to_change=fields_to_change,
                ) from ex

    def get_fields_to_change(
        self,
        copr_proj,
        additional_repos: Optional[List[str]] = None,
        chroots: Optional[List[str]] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        list_on_homepage: Optional[bool] = True,
        delete_after_days: Optional[int] = None,
    ) -> Dict[str, Tuple[Any, Any]]:

        fields_to_change: Dict[str, Tuple[Any, Any]] = {}
        if chroots is not None and set(copr_proj.chroot_repos.keys()) != set(chroots):
            fields_to_change["chroots"] = (
                copr_proj.chroot_repos.keys(),
                chroots,
            )
        if description and copr_proj.description != description:
            fields_to_change["description"] = (copr_proj.description, description)

        if instructions:
            if "instructions" not in copr_proj:
                logger.debug(
                    "The `instructions` key was not received from Copr. "
                    "We can't check that value to see if the update is needed."
                )
            elif copr_proj.instructions != instructions:
                fields_to_change["instructions"] = (
                    copr_proj.instructions,
                    instructions,
                )

        if list_on_homepage is not None:
            if "unlisted_on_hp" not in copr_proj:
                logger.debug(
                    "The `unlisted_on_hp` key was not received from Copr. "
                    "We can't check that value to see if the update is needed."
                )
            elif copr_proj.unlisted_on_hp != (not list_on_homepage):
                fields_to_change["unlisted_on_hp"] = (
                    copr_proj.unlisted_on_hp,
                    (not list_on_homepage),
                )

        if delete_after_days is not None:
            if "delete_after_days" not in copr_proj:
                logger.debug(
                    "The `delete_after_days` key was not received from Copr. "
                    "We can't check that value to see if the update is needed."
                )
            elif copr_proj.delete_after_days != delete_after_days:
                fields_to_change["delete_after_days"] = (
                    copr_proj.delete_after_days,
                    delete_after_days,
                )

        if additional_repos is not None and set(copr_proj.additional_repos) != set(
            additional_repos
        ):
            fields_to_change["additional_repos"] = (
                copr_proj.additional_repos,
                additional_repos,
            )

        return fields_to_change

    def create_copr_project(
        self,
        chroots: List[str],
        description: str,
        instructions: str,
        owner: str,
        project: str,
        list_on_homepage: bool = False,
        preserve_project: bool = False,
        additional_packages: List[str] = None,
        additional_repos: List[str] = None,
    ) -> None:

        try:
            self.copr_client.project_proxy.add(
                ownername=owner,
                projectname=project,
                chroots=chroots,
                description=(
                    description
                    or "Continuous builds initiated by packit service.\n"
                    "For more info check out https://packit.dev/"
                ),
                contact="https://github.com/packit/packit/issues",
                # don't show project on Copr homepage by default
                unlisted_on_hp=not list_on_homepage,
                # delete project after the specified period of time
                delete_after_days=60 if not preserve_project else None,
                additional_repos=additional_repos,
                instructions=instructions
                or "You can check out the upstream project "
                f"{self.upstream_local_project.git_url} to find out how to consume these builds. "
                f"This copr project is created and handled by the packit project "
                "(https://packit.dev/).",
            )
            # TODO: additional_packages
        except CoprException as ex:
            error = (
                f"Cannot create a new Copr project "
                f"(owner={owner} project={project} chroots={chroots}): {ex}"
            )
            logger.error(error)
            raise PackitCoprProjectException(error, ex)

    def watch_copr_build(
        self, build_id: int, timeout: int, report_func: Callable = None
    ) -> str:
        """ returns copr build state """
        watch_end = datetime.now() + timedelta(seconds=timeout)
        logger.debug(f"Watching copr build {build_id}.")
        state_reported = ""
        while True:
            build = self.copr_client.build_proxy.get(build_id)
            if build.state == state_reported:
                continue
            state_reported = build.state
            logger.debug(f"COPR build {build_id}, state = {state_reported}")
            try:
                gh_state, description = COPR2GITHUB_STATE[state_reported]
            except KeyError as exc:
                logger.error(f"COPR gave us an invalid state: {exc}")
                gh_state, description = "error", "Something went wrong."
            if report_func:
                report_func(
                    gh_state,
                    description,
                    build_id=build.id,
                    url=self.copr_web_build_url(build),
                )
            if gh_state != "pending":
                logger.debug(f"State is now {gh_state}, ending the watch.")
                return state_reported
            if datetime.now() > watch_end:
                logger.error(f"The build did not finish in time ({timeout}s).")
                report_func("error", "Build watch timeout")
                return state_reported
            time.sleep(10)

    def get_copr_builds(self, number_of_builds: int = 5) -> List:
        """
        Get the copr builds of this project done by packit.
        :return: list of builds
        """
        client = CoprClient.create_from_config_file()

        projects = [
            project.name
            for project in reversed(client.project_proxy.get_list(ownername="packit"))
            if project.name.startswith(
                f"{self.upstream_local_project.namespace}-{self.upstream_local_project.repo_name}-"
            )
        ][:5]

        builds: List = []
        for project in projects:
            builds += client.build_proxy.get_list(
                ownername="packit", projectname=project
            )

        logger.debug("Copr builds fetched.")
        return [(build.id, build.projectname, build.state) for build in builds][
            :number_of_builds
        ]
