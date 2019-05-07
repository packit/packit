import inspect
import json
import logging
from http.client import HTTPSConnection
from pathlib import Path
from typing import Type, Optional

import github
from ogr.abstract import GitService
from ogr.services.github import GithubService as GithubServiceOrigin
from ogr.services.github import GithubProject
from ogr.services.pagure import PagureService as PagureServiceOrigin

from packit.config import Config
from packit.exceptions import PackitException

READ_ONLY_NAME = "read_only"
logger = logging.getLogger(__name__)


def decorator_check_readonly(class_input: Type[object]) -> Type[object]:
    """
    Check Service Class and replace readonly parameter based if set and ogr  supports it
    otherwise remove this key and call ogr without that

    :param class_input: class object of ogr class what has to be changed if readonly mode is set
    :return: Class Object
    """

    def check_read_only_support(kls: Type[GitService]):
        if READ_ONLY_NAME not in inspect.signature(kls).parameters:
            raise PackitException("Read only mode is not supported by ogr library")

    # ignore this mypy type check because it is very dynamical and not able to properly wrote it
    class OutputClass(class_input):  # type: ignore
        def __init__(self, *args, **kwargs):
            if kwargs.get(READ_ONLY_NAME) is not None:
                if kwargs[READ_ONLY_NAME]:
                    check_read_only_support(class_input)
                else:
                    kwargs.pop(READ_ONLY_NAME)
            super().__init__(*args, **kwargs)

    return OutputClass


PagureService: Type[PagureServiceOrigin] = decorator_check_readonly(PagureServiceOrigin)
GithubService: Type[GithubServiceOrigin] = decorator_check_readonly(GithubServiceOrigin)


# TODO: upstream this to PyGithub
class BetterGithubIntegration(github.GithubIntegration):
    """
    A "fork" of GithubIntegration class from PyGithub.

    Since we auth as a Github app, we need to get an installation ID
    of the app within a repo. Then we are able to get the API token
    and work with Github's REST API
    """

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
        try:
            return str(data["id"])
        except KeyError:
            raise PackitException(
                f"This Github app is not installed in {namespace}/{repo}."
            )


# TODO: move as much logic to ogr as possible for these two functions
def get_github_service(
    config: Config, namespace: Optional[str] = None, repo: Optional[str] = None
) -> GithubServiceOrigin:
    """ initiate the GithubService """
    if config.github_app_id and config.github_app_cert_path and namespace and repo:
        logger.debug("Authenticating with Github using a Githab app.")
        private_key = Path(config.github_app_cert_path).read_text()
        integration = BetterGithubIntegration(config.github_app_id, private_key)
        inst_id = integration.get_installation_id_for_repo(namespace, repo)
        inst_auth = integration.get_access_token(inst_id)
        token = inst_auth.token
        gh_service = GithubService(token=token, read_only=config.dry_run)
    else:
        logger.debug("Authenticating with Github using a token.")
        gh_service = GithubService(token=config.github_token, read_only=config.dry_run)

    # test we have correct credentials
    # hmmm, Github tells me we are not allowed to this, we need to tick more perms
    # logger.debug(f"git service user = {gh_service.user.get_username()}")

    return gh_service


def get_github_project(
    config: Config,
    namespace: str,
    repo: str,
    service: Optional[GithubServiceOrigin] = None,
) -> GithubProject:
    github_service: GithubServiceOrigin = service or get_github_service(
        config, namespace=namespace, repo=repo
    )
    gh_proj = GithubProject(repo=repo, namespace=namespace, service=github_service)
    return gh_proj
