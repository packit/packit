# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import time
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Dict, Tuple, Any, Set

from cachetools.func import ttl_cache
from copr.v3 import Client as CoprClient
from copr.v3.exceptions import (
    CoprNoResultException,
    CoprException,
    CoprRequestException,
    CoprAuthException,
)
from munch import Munch
from packit.config import aliases  # so we can mock in tests
from packit.config.aliases import get_build_targets

from packit.constants import COPR2GITHUB_STATE, CHROOT_SPECIFIC_COPR_CONFIGURATION
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
        """Construct web frontend url because build.repo_url is not much user-friendly."""
        copr_url = self.copr_client.config.get("copr_url")
        return f"{copr_url}/coprs/build/{build.id}/"

    def get_copr_settings_url(
        self, owner: str, project: str, section: Optional[str] = None
    ):
        copr_url = self.copr_client.config.get("copr_url")
        section = section or "edit"

        # COPR groups starts with '@' but url have '/g/owner'
        if owner.startswith("@"):
            owner = f"g/{owner[1:]}"

        return f"{copr_url}/coprs/{owner}/{project}/{section}/"

    def get_valid_build_targets(
        self, *name: str, default: Optional[str] = aliases.DEFAULT_VERSION
    ) -> set:
        """
        For the provided iterable of names, expand them using get_build_targets() into valid
        Copr chhroot names and intersect this set with current available Copr chroots.

        :param name: name(s) of the system and version or target name. (passed to
                    packit.config.aliases.get_build_targets() function)
                or target name (e.g. "fedora-30-x86_64" or "fedora-stable-x86_64")
        :param default: used if no positional argument was given
        :return: set of build targets available also in copr chroots
        """
        build_targets = aliases.get_build_targets(*name, default=default)
        logger.info(f"Build targets: {build_targets} ")
        copr_chroots = self.get_available_chroots()
        logger.info(f"Copr chroots: {copr_chroots} ")
        logger.info(f"Result set: {set(build_targets) & set(copr_chroots)}")
        return set(build_targets) & set(copr_chroots)

    def _update_chroot_specific_configuration(
        self,
        project: str,
        owner: Optional[str] = None,
        targets_dict: Optional[Dict] = None,  # chroot specific configuration
    ):
        """
        Using the provided targets_dict, update chroot specific configuration
        """
        if targets_dict:
            # let's update chroot specific configuration
            for target, chroot_configuration in targets_dict.items():
                chroot_names = get_build_targets(target)
                for chroot_name in chroot_names:
                    if set(chroot_configuration.keys()).intersection(
                        CHROOT_SPECIFIC_COPR_CONFIGURATION.keys()
                    ):
                        logger.info(
                            f"There is chroot-specific configuration for {chroot_name}"
                        )
                        # only update when needed
                        copr_chroot_configuration = (
                            self.copr_client.project_chroot_proxy.get(
                                ownername=owner,
                                projectname=project,
                                chrootname=chroot_name,
                            )
                        )
                        update_dict = {}
                        for c, default in CHROOT_SPECIFIC_COPR_CONFIGURATION.items():
                            if copr_chroot_configuration.get(
                                c, default
                            ) != chroot_configuration.get(c, default):
                                update_dict[c] = chroot_configuration.get(c, default)
                        if update_dict:
                            logger.info(
                                f"Update {owner}/{project} {chroot_name}: {update_dict}"
                            )
                            self.copr_client.project_chroot_proxy.edit(
                                ownername=owner,
                                projectname=project,
                                chrootname=chroot_name,
                                **update_dict,
                            )

    def create_copr_project_if_not_exists(
        self,
        project: str,
        chroots: List[str],
        owner: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        list_on_homepage: Optional[bool] = False,
        preserve_project: Optional[bool] = False,
        additional_packages: Optional[List[str]] = None,
        additional_repos: Optional[List[str]] = None,
        request_admin_if_needed: bool = False,
        targets_dict: Optional[Dict] = None,  # chroot specific configuration
        module_hotfixes: bool = False,
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
                targets_dict=targets_dict,
                module_hotfixes=module_hotfixes,
            )
            return
        except CoprRequestException as ex:
            logger.debug(repr(ex))
            logger.error(
                f"We were not able to get copr project {owner}/{project}: {ex}"
            )
            raise

        delete_after_days: Optional[int] = (
            None if preserve_project is None else -1 if preserve_project else 60
        )

        self._update_chroot_specific_configuration(
            project, owner=owner, targets_dict=targets_dict
        )

        fields_to_change = self.get_fields_to_change(
            copr_proj=copr_proj,
            additional_repos=additional_repos,
            chroots=chroots,
            description=description,
            instructions=instructions,
            list_on_homepage=list_on_homepage,
            delete_after_days=delete_after_days,
            module_hotfixes=module_hotfixes,
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
            except CoprAuthException as ex:
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
        module_hotfixes: Optional[bool] = False,
    ) -> Dict[str, Tuple[Any, Any]]:

        fields_to_change: Dict[str, Tuple[Any, Any]] = {}
        if chroots is not None:
            old_chroots = self.get_chroots(copr_project=copr_proj)

            new_chroots = None
            if not set(chroots).issubset(old_chroots):
                new_chroots = list(set(chroots) | old_chroots)

            if new_chroots:
                new_chroots.sort()
                fields_to_change["chroots"] = (
                    list(old_chroots),
                    new_chroots,
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

        if module_hotfixes is not None and copr_proj.module_hotfixes != module_hotfixes:
            fields_to_change["module_hotfixes"] = (
                copr_proj.module_hotfixes,
                module_hotfixes,
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
        additional_packages: Optional[List[str]] = None,
        additional_repos: Optional[List[str]] = None,
        targets_dict: Optional[Dict] = None,  # chroot specific configuration
        module_hotfixes: bool = False,
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
                module_hotfixes=module_hotfixes,
            )
            # once created: update chroot-specific configuration if there is any
            self._update_chroot_specific_configuration(
                project, owner=owner, targets_dict=targets_dict
            )
        except CoprException as ex:
            # TODO: Remove once Copr doesn't throw for existing projects or new
            # API endpoint is established.
            if "You already have a project named" in ex.result.error:
                # race condition between workers
                logger.debug(f"Copr project ({owner}/{project}) is already present.")
                return

            error = (
                f"Cannot create a new Copr project "
                f"(owner={owner} project={project} chroots={chroots}): {ex}"
            )
            logger.error(error)
            logger.error(ex.result)
            raise PackitCoprProjectException(error) from ex

    def watch_copr_build(
        self, build_id: int, timeout: int, report_func: Callable = None
    ) -> str:
        """returns copr build state"""
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

    @staticmethod
    @ttl_cache(maxsize=1, ttl=timedelta(hours=12).seconds)
    def get_available_chroots() -> list:
        """
        Gets available copr chroots. Uses cache to avoid repetitive url fetching.

        Returns:
            List of valid chroots.
        """

        client = CoprClient.create_from_config_file()
        return list(
            filter(
                lambda chroot: not chroot.startswith("_"),
                client.mock_chroot_proxy.get_list().keys(),
            )
        )

    def get_build(self, build_id: int) -> Dict:
        """
        Get build details from Copr.

        Arguments:
            build_id -- Copr build id.

        :return: Dict
        """
        return self.copr_client.build_proxy.get(build_id)

    def get_repo_download_url(self, owner: str, project: str, chroot: str) -> str:
        """Provide a link to yum repo for the particular chroot"""
        copr_proj = self.copr_client.project_proxy.get(
            ownername=owner, projectname=project
        )
        try:
            return copr_proj["chroot_repos"][chroot]
        except KeyError:
            raise PackitCoprProjectException(
                f"There is no such target {chroot} in {owner}/{project}."
            )

    def get_chroots(
        self,
        owner: Optional[str] = None,
        project: Optional[str] = None,
        copr_project=None,
    ) -> Set[str]:
        """
        Get chroots set on a specific project. Use either `owner`+`project` or
        directly `copr_project`.

        Args:
            owner: Owner of the Copr project.
            project: Name of the Copr project.
            copr_project: Already fetched Copr project via project proxy of a
                Copr client.

        Returns:
            Set of all enabled chroots on the requested Copr project.
        """
        if not copr_project:
            copr_project = self.copr_client.project_proxy.get(
                ownername=owner, projectname=project
            )
        return set(copr_project.chroot_repos.keys())
