import functools
import inspect
import json
import logging
from http.client import HTTPSConnection
from pathlib import Path
from typing import Any, Type, Optional

import github
from ogr.abstract import GitService
from ogr.services.github import GithubService, GithubProject
from ogr.services.pagure import PagureService as PagureServiceOrigin

from packit.config import Config
from packit.exceptions import PackitException

READ_ONLY_NAME = "read_only"
logger = logging.getLogger(__name__)


def check_read_only_support(kls: Type[GitService]):
    if "read_only" not in inspect.signature(kls).parameters:
        raise PackitException("Read only mode is not supported by ogr library")


def decorator_check_readonly(class_object) -> Any:
    """
    Check Service Class and replace readonly parameter based if set and ogr  supports it
    otherwise remove this key and call ogr without that

    :param class_object: object of ogr class what has to be changed if readonly mode is set
    :return: Object instance
    """

    @functools.wraps(class_object)
    def output_class(*args, **kwargs):
        if kwargs[READ_ONLY_NAME]:
            check_read_only_support(class_object)
            return class_object(*args, **kwargs)
        kwargs.pop(READ_ONLY_NAME)
        return class_object(*args, **kwargs)

    return output_class


PagureService: PagureServiceOrigin = decorator_check_readonly(PagureServiceOrigin)


class BetterGithubIntegration(github.GithubIntegration):
    def get_installation_id_for_repo(self, namespace: str, repo: str) -> str:
        """
        Get repo installation ID for a repository
        """
        conn = HTTPSConnection("api.github.com")
        conn.request(
            method="GET",
            url=f"/repos/{namespace}/{repo}/installation",
            headers={
                "Authorization": "Bearer {}".format(self.create_jwt()),
                "Accept": "application/vnd.github.machine-man-preview+json",
                "User-Agent": "PyGithub/Python",
            },
            body=None,
        )
        response = conn.getresponse()
        response_text = response.read()
        data = json.loads(response_text)
        if response.status != 200:
            logger.debug(response_text)
            raise PackitException(
                f"Unable to obtain installation ID for repo {namespace}/{repo}."
            )
        return str(data["id"])


# TODO: move as much logic to ogr as possible for these two functions
def get_github_service(
    config: Config, namespace: Optional[str] = None, repo: Optional[str] = None
) -> GithubService:
    """ initiate the GithubService """
    gh_service_kls: Type[GithubService] = decorator_check_readonly(GithubService)
    if config.github_app_id and config.github_app_cert_path and namespace and repo:
        logger.debug("Authenticating with Github using a Githab app.")
        private_key = Path(config.github_app_cert_path).read_text()
        integration = BetterGithubIntegration(config.github_app_id, private_key)
        inst_id = integration.get_installation_id_for_repo(namespace, repo)
        inst_auth = integration.get_access_token(inst_id)
        token = inst_auth.token
        gh_service = gh_service_kls(token=token, read_only=config.dry_run)
    else:
        logger.debug("Authenticating with Github using a token.")
        gh_service = gh_service_kls(token=config.github_token, read_only=config.dry_run)

    # test we have correct credentials
    # hmmm, Github tells me we are not allowed to this, we need to tick more perms
    # logger.debug(f"git service user = {gh_service.user.get_username()}")

    return gh_service


def get_github_project(
    config: Config, namespace: str, repo: str, service: Optional[GithubService] = None
) -> GithubProject:
    github_service: GithubService = service or get_github_service(
        config, namespace=namespace, repo=repo
    )
    gh_proj = GithubProject(repo=repo, namespace=namespace, service=github_service)
    return gh_proj
