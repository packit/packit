# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import tempfile
from pathlib import Path
from typing import Tuple, Optional, Union, List

import git
from ogr.parsing import parse_git_repo
from packit.utils.commands import run_command

from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


def is_git_repo(directory: Union[Path, str]) -> bool:
    """
    Test, if the directory is a git repo.
    (Has .git subdirectory?)
    """
    return Path(directory, ".git").is_dir()


def get_repo(url: str, directory: Union[Path, str] = None) -> git.Repo:
    """
    Use directory as a git repo or clone repo to the tempdir.
    """
    directory = str(directory) if directory else tempfile.mkdtemp()

    if is_git_repo(directory=directory):
        logger.debug(f"Repo already exists in {directory}.")
        repo = git.repo.Repo(directory)
    else:
        logger.debug(f"Cloning repo {url} -> {directory}")
        repo = git.repo.Repo.clone_from(url=url, to_path=directory, tags=True)

    return repo


def get_namespace_and_repo_name(url: str) -> Tuple[Optional[str], str]:
    parsed_git_repo = parse_git_repo(url)
    if parsed_git_repo is None or not parsed_git_repo.repo:
        raise PackitException(
            f"Invalid URL format, can't obtain namespace and repository name: {url}"
        )
    return parsed_git_repo.namespace, parsed_git_repo.repo


def is_a_git_ref(repo: git.Repo, ref: str) -> bool:
    try:
        commit = repo.commit(ref)
        return bool(commit)
    except git.BadName:
        return False


def git_remote_url_to_https_url(inp: str) -> str:
    """
    turn provided git remote URL to https URL:
    returns empty string if the input can't be processed
    """
    logger.debug(f"Parsing git remote URL {inp!r} and converting it to https-like URL.")
    parsed_repo = parse_git_repo(inp)
    if not parsed_repo or not parsed_repo.hostname:
        logger.debug(f"{inp!r} is not an URL we recognize.")
        return ""

    if inp.startswith(("http", "https")):
        logger.debug(f"Provided input {inp!r} is an url.")
        return inp

    optional_suffix = ".git" if inp.endswith(".git") else ""
    url_str = "https://{}/{}/{}{}".format(
        parsed_repo.hostname, parsed_repo.namespace, parsed_repo.repo, optional_suffix
    )

    logger.debug(f"URL {inp!r} turned into HTTPS {url_str!r}")
    return url_str


def get_current_version_command(
    glob_pattern: str, refs: Optional[str] = "tags"
) -> List[str]:
    """
    Returns command that find latest git reference matching given pattern.

    :param glob_pattern: pattern that is used to find latest ref
    :param refs: specifies what kind of ref is used; \
        default is `"tags"` that searches through all tags (including non-annotated), \
        pass `None` to search only annotated tags or `"all"` to search through \
        all refs (including branches and remote refs)
    :return: command to find latest ref
    """
    return [
        "git",
        "describe",
        "--abbrev=0",
        f"--{refs}" if refs else "",
        "--match",
        glob_pattern,
    ]


def clone_centos_package(
    package_name: str,
    dist_git_path: Path,
    branch: str = "c8s",
    namespace: str = "rpms",
    stg: bool = False,
):
    """
    clone selected package from git.[stg.]centos.org
    """
    run_command(
        [
            "git",
            "clone",
            "-b",
            branch,
            f"https://git{'.stg' if stg else ''}.centos.org/{namespace}/{package_name}.git",
            str(dist_git_path),
        ]
    )


def clone_fedora_package(
    package_name: str,
    dist_git_path: Path,
    branch: str = "c8s",
    namespace: str = "rpms",
    stg: bool = False,
):
    """
    clone selected package from Fedora's src.fedoraproject.org
    """
    run_command(
        [
            "git",
            "clone",
            "-b",
            branch,
            f"https://src{'.stg' if stg else ''}.fedoraproject.org/{namespace}/{package_name}.git",
            str(dist_git_path),
        ]
    )
