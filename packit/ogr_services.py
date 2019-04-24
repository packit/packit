import inspect
import functools
from typing import Any
from packit.exceptions import PackitException
from ogr.services.github import GithubService as GithubServiceOrigin
from ogr.services.pagure import PagureService as PagureServiceOrigin

READ_ONLY_NAME = "read_only"


def check_read_only_support():
    if "read_only" not in inspect.signature(GithubServiceOrigin).parameters:
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
            check_read_only_support()
            return class_object(*args, **kwargs)
        kwargs.pop(READ_ONLY_NAME)
        return class_object(*args, **kwargs)

    return output_class


GithubService: GithubServiceOrigin = decorator_check_readonly(GithubServiceOrigin)
PagureService: PagureServiceOrigin = decorator_check_readonly(PagureServiceOrigin)
