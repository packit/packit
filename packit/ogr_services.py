import inspect
from packit.exceptions import PackitException
from ogr.services.github import GithubService as GithubServiceOrigin
from ogr.services.pagure import PagureService as PagureServiceOrigin


if "read_only" not in inspect.signature(GithubServiceOrigin).parameters:
    raise PackitException("Read only mode is not supported by ogr library")

GithubService = GithubServiceOrigin
PagureService = PagureServiceOrigin
