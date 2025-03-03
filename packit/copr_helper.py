# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import backoff
from cachetools.func import ttl_cache
from copr.v3 import Client as CoprClient
from copr.v3.exceptions import (
    CoprAuthException,
    CoprException,
    CoprNoResultException,
    CoprRequestException,
)
from munch import Munch

from packit.config import aliases  # so we can mock in tests
from packit.config.aliases import get_build_targets
from packit.config.common_package_config import MockBootstrapSetup
from packit.constants import CHROOT_SPECIFIC_COPR_CONFIGURATION, COPR2GITHUB_STATE
from packit.exceptions import PackitCoprProjectException, PackitCoprSettingsException
from packit.local_project import LocalProject

logger = logging.getLogger(__name__)


def not_copr_race_condition(e):
    is_race_condition = "already exists" in str(e) and "400" in str(e)
    if is_race_condition:
        logger.debug(f"Probably a Copr race condition: {e}, try again.")
    return not is_race_condition


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
        self,
        owner: str,
        project: str,
        section: Optional[str] = None,
    ):
        copr_url = self.copr_client.config.get("copr_url")
        section = section or "edit"

        # COPR groups starts with '@' but url have '/g/owner'
        if owner.startswith("@"):
            owner = f"g/{owner[1:]}"

        return f"{copr_url}/coprs/{owner}/{project}/{section}/"

    def get_valid_build_targets(
        self,
        *name: str,
        default: Optional[str] = aliases.DEFAULT_VERSION,
    ) -> set:
        """
        For the provided iterable of names, expand them using get_build_targets() into valid
        Copr chhroot names and intersect this set with current available Copr chroots.

        Args:
            name: name(s) of the system and version or target name. (passed to
                    packit.config.aliases.get_build_targets() function)
                or target name (e.g. "fedora-30-x86_64" or "fedora-stable-x86_64")
            default: used if no positional argument was given

        Returns:
            Set of build targets available also in copr chroots.
        """
        build_targets = aliases.get_build_targets(*name, default=default)
        logger.info(f"Build targets: {build_targets} ")
        copr_chroots = self.get_available_chroots()
        logger.info(f"Result set: {set(build_targets) & set(copr_chroots)}")
        return set(build_targets) & set(copr_chroots)

    def _get_chroot_specific_configuration_to_update(
        self,
        project: str,
        owner: Optional[str] = None,
        targets_dict: Optional[dict] = None,  # chroot specific configuration
    ) -> dict[str, dict[str, tuple]]:
        """
        Using the provided targets_dict, update chroot specific configuration
        """
        if not targets_dict:
            return {}

        update_dict = {}
        # let's get the chroot specific configuration to update
        for target, chroot_configuration in targets_dict.items():
            chroot_names = get_build_targets(target)
            for chroot_name in chroot_names:
                if set(chroot_configuration.keys()).intersection(
                    CHROOT_SPECIFIC_COPR_CONFIGURATION.keys(),
                ):
                    logger.info(
                        f"There is chroot-specific configuration for {chroot_name}",
                    )
                    # only update when needed
                    try:
                        copr_chroot_configuration = (
                            self.copr_client.project_chroot_proxy.get(
                                ownername=owner,
                                projectname=project,
                                chrootname=chroot_name,
                            )
                        )
                    except CoprNoResultException:
                        logger.debug(
                            "It was not possible to get chroot configuration for "
                            f"{chroot_name}",
                        )
                        continue

                    update_dict_chroot = {}
                    for c, default in CHROOT_SPECIFIC_COPR_CONFIGURATION.items():
                        if (
                            old_value := copr_chroot_configuration.get(
                                c,
                                default,
                            )
                        ) != (new_value := chroot_configuration.get(c, default)):
                            update_dict_chroot[c] = (old_value, new_value)
                    if update_dict_chroot:
                        update_dict[chroot_name] = update_dict_chroot
        return update_dict

    def _update_chroot_specific_configuration(
        self,
        owner: str,
        project: str,
        update_dict: dict[str, dict[str, tuple]],
    ):
        for chroot, update_dict_chroot in update_dict.items():
            diff_string = [
                f"{field}: {old} -> {new}"
                for field, (old, new) in update_dict_chroot.items()
            ]
            logger.info(
                f"Update {owner}/{project} {chroot}: {diff_string}",
            )
            update_args = {
                field: new_value
                for field, (old_value, new_value) in update_dict_chroot.items()
            }
            self.copr_client.project_chroot_proxy.edit(
                ownername=owner,
                projectname=project,
                chrootname=chroot,
                **update_args,
            )

    @backoff.on_exception(
        backoff.expo,
        PackitCoprProjectException,
        max_time=120,
        giveup=not_copr_race_condition,
    )
    def create_or_update_copr_project(
        self,
        project: str,
        chroots: list[str],
        owner: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        list_on_homepage: Optional[bool] = False,
        preserve_project: Optional[bool] = False,
        additional_packages: Optional[list[str]] = None,
        additional_repos: Optional[list[str]] = None,
        bootstrap: Optional[MockBootstrapSetup] = None,
        request_admin_if_needed: bool = False,
        targets_dict: Optional[dict] = None,  # chroot specific configuration
        module_hotfixes: bool = False,
        follow_fedora_branching: bool = False,
    ) -> None:
        """
        Create or update a project in copr.

        Raises:
             PackitCoprException on any problems.
        """
        default_description = (
            "Continuous builds initiated by Packit service.\n"
            "For more info check out https://packit.dev/"
        )

        default_instructions = (
            (
                "You can check out the upstream project "
                f"{self.upstream_local_project.git_url} to find out how to consume these builds. "
                f"This copr project is created and handled by the Packit project "
                "(https://packit.dev/)."
            )
            if self.upstream_local_project
            else None
        )

        delete_after_days: Optional[int] = (
            None if preserve_project is None else -1 if preserve_project else 60
        )

        logger.info(f"Creating {owner}/{project} Copr project.")
        try:
            copr_proj = self.copr_client.project_proxy.add(
                ownername=owner,
                projectname=project,
                chroots=chroots,
                description=description or default_description,
                contact="https://github.com/packit/packit/issues",
                # don't show project on Copr homepage by default
                unlisted_on_hp=not list_on_homepage,
                # delete project after the specified period of time
                delete_after_days=delete_after_days,
                additional_repos=additional_repos,
                bootstrap=bootstrap.value if bootstrap is not None else None,
                instructions=instructions or default_instructions,
                module_hotfixes=module_hotfixes,
                follow_fedora_branching=follow_fedora_branching,
                exist_ok=True,
            )
        except (CoprException, CoprRequestException) as ex:
            response = ex.result.__response__
            if response and response.status_code >= 500:
                error = (
                    f"Packit received HTTP {response.status_code} {response.reason} "
                    "from Copr Service. "
                    "Check the Copr status page: https://copr.fedorainfracloud.org/status/stats/, "
                    "or ask for help in Fedora Build System matrix channel: "
                    "https://matrix.to/#/#buildsys:fedoraproject.org."
                )
                logger.debug(
                    f"Unexpected Copr error: {response.status_code} {response.reason}: "
                    f"{response.text}",
                )
            else:
                error = (
                    f"Cannot create a new Copr project "
                    f"(owner={owner} project={project} chroots={chroots}): {ex}."
                )
                if response:
                    error += f" Copr HTTP response is {response.status_code} {response.reason}."
            logger.error(error)
            logger.error(ex.result)
            raise PackitCoprProjectException(error) from ex

        fields_to_change = self.get_fields_to_change(
            copr_proj=copr_proj,
            additional_repos=additional_repos,
            chroots=chroots,
            description=description,
            instructions=instructions,
            list_on_homepage=list_on_homepage,
            delete_after_days=delete_after_days,
            module_hotfixes=module_hotfixes,
            bootstrap=bootstrap,
        )
        try:
            if fields_to_change:
                failure_message = (
                    f"Copr project update failed for '{owner}/{project}' project."
                )
                self.update_copr_project(owner, project, fields_to_change)

            failure_message = (
                f"Copr project chroot configuration update failed "
                f"for '{owner}/{project}' project."
            )
            chroot_specific_config_to_update = (
                self._get_chroot_specific_configuration_to_update(
                    project,
                    owner,
                    targets_dict,
                )
            )

            # transform the dict for the user message purposes
            fields_to_change = {
                f"{chroot}: {field}": values
                for chroot, chroot_config in chroot_specific_config_to_update.items()
                for field, values in chroot_config.items()
            }

            self._update_chroot_specific_configuration(
                project=project,
                owner=owner,
                update_dict=chroot_specific_config_to_update,
            )

        except CoprAuthException as ex:
            if "Only owners and admins may update their projects." in str(ex):
                if request_admin_if_needed:
                    logger.info(
                        "Admin permissions are required "
                        "in order to be able to edit project settings. "
                        "Requesting the admin rights for the "
                        f"copr '{owner}/{project}' project.",
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
                        f"when using Packit CLI.",
                    )
            raise PackitCoprSettingsException(
                failure_message,
                fields_to_change=fields_to_change,
            ) from ex

    def update_copr_project(
        self,
        owner: str,
        project: str,
        fields_to_change: dict[str, tuple],
    ):
        logger.info(f"Updating copr project '{owner}/{project}'")
        for field, (old, new) in fields_to_change.items():
            logger.debug(f"{field}: {old} -> {new}")
            kwargs: dict[str, Any] = {
                arg_name: new for arg_name, (old, new) in fields_to_change.items()
            }
            logger.debug(f"Copr edit arguments: {kwargs}")
            self.copr_client.project_proxy.edit(
                ownername=owner,
                projectname=project,
                **kwargs,
            )

    def get_fields_to_change(
        self,
        copr_proj,
        additional_repos: Optional[list[str]] = None,
        chroots: Optional[list[str]] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        list_on_homepage: Optional[bool] = True,
        delete_after_days: Optional[int] = None,
        module_hotfixes: Optional[bool] = False,
        bootstrap: Optional[MockBootstrapSetup] = None,
    ) -> dict[str, tuple[Any, Any]]:
        fields_to_change: dict[str, tuple[Any, Any]] = {}
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
                    "We can't check that value to see if the update is needed.",
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
                    "We can't check that value to see if the update is needed.",
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
                    "We can't check that value to see if the update is needed.",
                )
            elif copr_proj.delete_after_days != delete_after_days:
                fields_to_change["delete_after_days"] = (
                    copr_proj.delete_after_days,
                    delete_after_days,
                )

        if additional_repos is not None and set(copr_proj.additional_repos) != set(
            additional_repos,
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

        if bootstrap is not None and copr_proj.bootstrap != bootstrap.value:
            fields_to_change["bootstrap"] = (
                copr_proj.bootstrap,
                bootstrap.value,
            )

        return fields_to_change

    def watch_copr_build(
        self,
        build_id: int,
        timeout: int,
        report_func: Optional[Callable] = None,
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

    def get_copr_builds(self, number_of_builds: int = 5) -> list:
        """
        Get the copr builds of this project done by packit.

        Returns:
            List of builds.
        """
        client = CoprClient.create_from_config_file()

        projects = [
            project.name
            for project in reversed(client.project_proxy.get_list(ownername="packit"))
            if project.name.startswith(
                f"{self.upstream_local_project.namespace}-{self.upstream_local_project.repo_name}-",
            )
        ][:5]

        builds: list = []
        for project in projects:
            builds += client.build_proxy.get_list(
                ownername="packit",
                projectname=project,
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
            ),
        )

    def get_build(self, build_id: int) -> dict:
        """
        Get build details from Copr.

        Args:
            build_id: Copr build id.

        Returns:
             Dict of build details.
        """
        return self.copr_client.build_proxy.get(build_id)

    def cancel_build(self, build_id: int) -> bool:
        """
        Cancel a build with given ID.

        Args:
            build_id: Copr build ID.

        Returns:
            Whether the cancelling was successful.
        """
        logger.info(f"Cancelling build with ID {build_id}")
        try:
            self.copr_client.build_proxy.cancel(build_id)
            return True
        except CoprRequestException as ex:
            logger.error(f"Failed to cancel build {build_id}: {ex}")
            return False

    def get_repo_download_url(self, owner: str, project: str, chroot: str) -> str:
        """Provide a link to yum repo for the particular chroot"""
        copr_proj = self.copr_client.project_proxy.get(
            ownername=owner,
            projectname=project,
        )
        try:
            return copr_proj["chroot_repos"][chroot]
        except KeyError as e:
            raise PackitCoprProjectException(
                f"There is no such target {chroot} in {owner}/{project}.",
            ) from e

    def get_chroots(
        self,
        owner: Optional[str] = None,
        project: Optional[str] = None,
        copr_project=None,
    ) -> set[str]:
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
                ownername=owner,
                projectname=project,
            )
        return set(copr_project.chroot_repos.keys())
