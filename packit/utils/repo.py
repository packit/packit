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
import re
import tempfile
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse

import git

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
    if Path(url).exists():
        return None, Path(url).name
    url = url.strip("/")
    try:
        if url.endswith(".git"):
            url = url[:-4]
        if url.startswith("http"):
            # if git_url is in format http{s}://github.com/org/repo_name
            _, namespace, repo_name = url.rsplit("/", 2)
        else:
            # If git_url is in format git@github.com:org/repo_name
            org_repo = url.split(":", 2)[1]
            namespace, repo_name = org_repo.split("/", 2)
    except (IndexError, ValueError) as ex:
        raise PackitException(
            f"Invalid URL format, can't obtain namespace and repository name: {url}: {ex!r}"
        )
    return namespace, repo_name


def is_a_git_ref(repo: git.Repo, ref: str) -> bool:
    try:
        commit = repo.commit(ref)
        return bool(commit)
    except git.BadName:
        return False


# TODO: merge this function into parse_git_repo in ogr
# https://github.com/packit-service/packit/pull/555#discussion_r332871418
def git_remote_url_to_https_url(inp: str) -> str:
    """
    turn provided git remote URL to https URL:
    returns empty string if the input can't be processed
    """
    if not inp:
        return ""
    parsed = urlparse(inp)
    if parsed.scheme and parsed.scheme in ["http", "https"]:
        logger.debug(f"Provided input {inp!r} is an url.")
        return inp
    elif "@" in inp:
        url_str = inp.replace("ssh://", "")
        # now we can sub the colon (:) with slash (/)
        url_str = url_str.replace(":", "/")
        # and finally, get rid of the git@ junk
        url_str = re.sub(r"\w+@", "https://", url_str)
        # let's verify it's good
        try:
            urlparse(url_str)
        except Exception:
            logger.error(f"Unable to process {inp!r}.")
            raise PackitException(f"Unable to process {inp}.")
        else:
            logger.debug(f"SSH style URL {inp!r} turned into HTTPS {url_str!r}")
            return url_str
    logger.warning(f"{inp!r} is not an URL we recognize.")
    return ""
