# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

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
import tempfile
from pathlib import Path
from typing import Tuple, Optional

import git

from ogr.parsing import parse_git_repo
from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


def is_git_repo(directory: str) -> bool:
    """
    Test, if the directory is a git repo.
    (Has .git subdirectory?)
    """
    return Path(directory).joinpath(".git").is_dir()


def get_repo(url: str, directory: str = None) -> git.Repo:
    """
    Use directory as a git repo or clone repo to the tempdir.
    """
    if not directory:
        tempdir = tempfile.mkdtemp()
        directory = tempdir

    # TODO: optimize cloning: single branch and last n commits?
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
    parsed_repo = parse_git_repo(inp)
    if not parsed_repo or not parsed_repo.hostname:
        logger.warning(f"{inp!r} is not an URL we recognize.")
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
