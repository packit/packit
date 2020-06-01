import logging
from datetime import datetime, timedelta
from typing import Callable, List, Optional

import time
from copr.v3 import Client as CoprClient
from copr.v3.exceptions import CoprNoResultException, CoprException
from munch import Munch

from packit.constants import COPR2GITHUB_STATE
from packit.exceptions import PackitCoprProjectException
from packit.local_project import LocalProject

logger = logging.getLogger(__name__)


class CoprHelper:
    def __init__(self, upstream_local_project: LocalProject) -> None:
        self.upstream_local_project = upstream_local_project
        self._copr_client = None

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

    def create_copr_project_if_not_exists(
        self,
        project: str,
        chroots: List[str],
        owner: str = None,
        description: str = None,
        instructions: str = None,
    ) -> None:
        """
        Create a project in copr if it does not exists.

        Raises PackitCoprException on any problems.
        """
        try:
            copr_proj = self.copr_client.project_proxy.get(
                ownername=owner, projectname=project
            )
            # make sure or project has chroots set correctly
            if set(copr_proj.chroot_repos.keys()) != set(chroots):
                logger.info(f"Updating targets on project '{owner}/{project}'")
                logger.debug(f"old = {set(copr_proj.chroot_repos.keys())}")
                logger.debug(f"new = {set(chroots)}")
                self.copr_client.project_proxy.edit(
                    owner,
                    project,
                    chroots=chroots,
                    description=description,
                    instructions=instructions,
                )
        except CoprNoResultException as ex:
            if owner != self.configured_owner:
                raise PackitCoprProjectException(
                    f"Copr project {owner}/{project} not found."
                ) from ex

            logger.info(f"Copr project '{owner}/{project}' not found. Creating new.")
            self.create_copr_project(chroots, description, instructions, owner, project)

    def create_copr_project(
        self,
        chroots: List[str],
        description: str,
        instructions: str,
        owner: str,
        project: str,
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
                contact="https://github.com/packit-service/packit/issues",
                # don't show project on Copr homepage
                unlisted_on_hp=True,
                # delete project after the specified period of time
                delete_after_days=60,
                instructions=instructions
                or "You can check out the upstream project "
                f"{self.upstream_local_project.git_url} to find out how to consume these builds. "
                f"This copr project is created and handled by the packit project "
                "(https://packit.dev/).",
            )
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
