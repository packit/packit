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

import json
import logging
import os
import re
import shlex
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Tuple, Any, Optional, Dict
from urllib.parse import urlparse

import git
from pkg_resources import get_distribution, DistributionNotFound

from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


def get_rev_list_kwargs(opt_list):
    """
    Converts the list of 'key=value' options to dict.
    Options without value gets True as a value.
    """
    result = {}
    for opt in opt_list:
        opt_split = opt.split(sep="=", maxsplit=1)
        if len(opt_split) == 1:
            result[opt] = True
        else:
            key, raw_val = opt_split
            try:
                val = json.loads(raw_val.lower())
                result[key] = val
            except json.JSONDecodeError:
                result[key] = raw_val
    return result


def run_command(
    cmd,
    error_message=None,
    cwd=None,
    fail=True,
    output=False,
    env: Optional[Dict] = None,
):
    if not isinstance(cmd, list):
        cmd = shlex.split(cmd)

    logger.debug("cmd = '%s'", " ".join(cmd))

    cwd = cwd or str(Path.cwd())
    error_message = error_message or f"Command {cmd} failed."

    # we need to pass complete env to Popen, otherwise we lose everything from os.environ
    cmd_env = os.environ
    if env:
        cmd_env.update(env)

    shell = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=cwd,
        universal_newlines=True,
        env=cmd_env,
    )

    stdout = shell.stdout.strip()
    stderr = shell.stderr.strip()
    if stdout:
        logger.debug("STDOUT: %s", stdout)
    if stderr:
        logger.info("STDERR: %s", stderr)

    if shell.returncode != 0:
        logger.error("Command %s failed", shell.args)
        logger.error("%s", error_message)
        if fail:
            raise PackitException(f"Command {shell.args!r} failed: {error_message}")
        success = False
    else:
        success = True

    if not output:
        return success

    return shell.stdout


def run_command_remote(
    cmd,
    error_message=None,
    cwd=None,
    fail=True,
    output=False,
    env: Optional[Dict] = None,
):
    """
    wrapper for run_command method
    Indicating that this command run some action without local effect,
    or the effect is not important.

    eg.
        submit something to some server, and check how server reply
        call kinit of some ticket
    """
    return run_command(cmd, error_message, cwd, fail, output, env)


class PackitFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            self._style._fmt = "%(message)s"
        elif record.levelno > logging.INFO:
            self._style._fmt = "%(levelname)-8s %(message)s"
        else:  # debug
            self._style._fmt = (
                "%(asctime)s.%(msecs).03d %(filename)-17s %(levelname)-6s %(message)s"
            )
        return logging.Formatter.format(self, record)


def set_logging(
    logger_name="packit",
    level=logging.INFO,
    handler_class=logging.StreamHandler,
    handler_kwargs=None,
    date_format="%H:%M:%S",
):
    """
    Set personal logger for this library.

    :param logger_name: str, name of the logger
    :param level: int, see logging.{DEBUG,INFO,ERROR,...}: level of logger and handler
    :param handler_class: logging.Handler instance, default is StreamHandler (/dev/stderr)
    :param handler_kwargs: dict, keyword arguments to handler's constructor
    :param date_format: str, date style in the logs
    """
    if level != logging.NOTSET:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.debug(f"logging set to {logging.getLevelName(level)}")

        # do not readd handlers if they are already present
        if not [x for x in logger.handlers if isinstance(x, handler_class)]:
            handler_kwargs = handler_kwargs or {}
            handler = handler_class(**handler_kwargs)
            handler.setLevel(level)

            formatter = PackitFormatter(None, date_format)
            handler.setFormatter(formatter)
            logger.addHandler(handler)


def commits_to_nice_str(commits):
    return "\n".join(
        f"{commit.summary}\n"
        f"Author: {commit.author.name} <{commit.author.email}>\n"
        f"{commit.hexsha}\n"
        for commit in commits
    )


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
        logger.debug(f"Repo already exists in {directory}")
        repo = git.repo.Repo(directory)
    else:
        logger.debug(f"Cloning repo: {url} -> {directory}")
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


def assert_existence(obj):
    """
    Force the lazy object to be evaluated.
    """
    if obj is None:
        raise PackitException("Object needs to have a value.")


def nested_get(d: dict, *keys, default=None) -> Any:
    """
    recursively obtain value from nested dict

    :param d: dict
    :param keys: path within the structure
    :param default: a value to return by default

    :return: value or None
    """
    response = d
    for k in keys:
        try:
            response = response[k]
        except (KeyError, AttributeError, TypeError):
            # logger.debug("can't obtain %s: %s", k, ex)
            return default
    return response


def is_a_git_ref(repo: git.Repo, ref: str) -> bool:
    try:
        commit = repo.commit(ref)
        return bool(commit)
    except git.BadName:
        return False


@contextmanager
def cwd(target):
    """
    Manage cwd in a pushd/popd fashion.

    Usage:

        with cwd(tmpdir):
          do something in tmpdir
    """
    curdir = os.getcwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(curdir)


def rpmdev_bumpspec(
    specfile_path: Path, comment: str, version: str, changelog_file: str = None
):
    """
    wrapper on top of rpmdev-bumpspec utility

    :return:
    """
    cmd = ["rpmdev-bumpspec", f"--comment={comment}", f"--new={version}"]
    if changelog_file:
        cmd += [f"--file={changelog_file}"]
    cmd += [str(specfile_path)]
    run_command(cmd)


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
        logger.debug(f"Provided input {inp} is an url.")
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
            logger.error(f"unable to process {inp}")
            raise PackitException(f"Unable to process {inp}.")
        else:
            logger.debug(f"SSH style URL {inp} turned into HTTPS {url_str}")
            return url_str
    logger.warning(f"{inp} is not an URL we recognize")
    return ""


def get_packit_version() -> str:
    try:
        return get_distribution("packitos").version
    except DistributionNotFound:
        return "NOT_INSTALLED"
