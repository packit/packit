import json
import logging
from http.client import HTTPSConnection
from pathlib import Path
from typing import Optional

import github
from ogr.mock_core import PersistentObjectStorage
from ogr.services.github import GithubProject, GithubService

from packit.config import Config
from packit.exceptions import PackitException

READ_ONLY_NAME = "read_only"
logger = logging.getLogger(__name__)


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
) -> GithubService:
    """ initiate the GithubService """
    if config.github_app_id and config.github_app_cert_path and namespace and repo:
        logger.debug("Authenticating with Github using a Githab app.")
        private_key = Path(config.github_app_cert_path).read_text()
        integration = BetterGithubIntegration(config.github_app_id, private_key)
        inst_id = integration.get_installation_id_for_repo(namespace, repo)
        inst_auth = integration.get_access_token(inst_id)
        token = inst_auth.token
        gh_service_kwargs = dict(token=token, read_only=config.dry_run)
    else:
        logger.debug("Authenticating with Github using a token.")
        gh_service_kwargs = dict(token=config.github_token, read_only=config.dry_run)
    if config.github_requests_log_path:
        if config.github_token:
            write_mode = True
        else:
            write_mode = False
        s = PersistentObjectStorage(
            storage_file=config.github_requests_log_path,
            is_write_mode=write_mode,
            dump_after_store=True,
        )
        gh_service_kwargs.update(dict(persistent_storage=s))
    gh_service = GithubService(**gh_service_kwargs)

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
