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
import sys
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Tuple, Any, Optional, Dict, Union, List
from urllib.parse import urlparse

import git
from pkg_resources import get_distribution, DistributionNotFound

from packit.exceptions import PackitException, PackitCommandFailedError

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


class StreamLogger(threading.Thread):
    def __init__(self, stream, log_level=logging.DEBUG, decode=False):
        super().__init__(daemon=True)
        self.stream = stream
        self.output = []
        self.log_level = log_level
        self.decode = decode

    def run(self):
        for line in self.stream:
            # not doing strip here on purpose so we get real output
            # and we are saving bytes b/c the output can contain chars which can't be decoded
            self.output.append(line)
            line = line.rstrip(b"\n")
            if self.decode:
                line = line.decode()
            logger.log(self.log_level, line)

    def get_output(self):
        return b"".join(self.output)


def run_command(
    cmd: Union[List[str], str],
    error_message: str = None,
    cwd: Union[str, Path] = None,
    fail: bool = True,
    output: bool = False,
    env: Optional[Dict] = None,
    decode: bool = True,
    print_live: bool = False,
):
    """
    run provided command in a new subprocess

    :param cmd: 'duh
    :param error_message: if the command fails, output this error message
    :param cwd: run the command in
    :param fail: raise an exception when the command fails
    :param output: if True, return command's stdout & stderr
    :param env: set these env vars in the subprocess
    :param decode: decode stdout from utf8 to string
    :param print_live: print output from the command realtime to INFO log
    """
    if not isinstance(cmd, list):
        cmd = shlex.split(cmd)

    escaped_command = " ".join(cmd)

    logger.debug(f"Command: {escaped_command}")

    cwd = str(cwd) if cwd else str(Path.cwd())
    error_message = error_message or f"Command {escaped_command!r} failed."

    # we need to pass complete env to Popen, otherwise we lose everything from os.environ
    cmd_env = os.environ
    if env:
        cmd_env.update(env)

    # we can't use universal newlines here b/c the output from the command can be encoded
    # in something alien and we would "can't decode this using utf-8" errors
    # https://github.com/packit-service/systemd-rhel8-flock/pull/9#issuecomment-550184016
    shell = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=cwd,
        env=cmd_env,
    )

    stdout = StreamLogger(
        shell.stdout,
        log_level=logging.DEBUG if not print_live else logging.INFO,
        decode=decode,
    )
    stderr = StreamLogger(
        shell.stderr,
        log_level=logging.DEBUG if not print_live else logging.INFO,
        decode=decode,
    )

    stdout.start()
    stderr.start()
    shell.wait()
    stdout.join()
    stderr.join()

    if shell.returncode != 0:
        logger.error(f"{error_message}")
        if fail:
            stderr_output = (
                stderr.get_output().decode() if decode else stderr.get_output()
            )
            stdout_output = (
                stdout.get_output().decode() if decode else stdout.get_output()
            )
            if output:
                logger.debug(f"Command stderr: {stderr_output}")
                logger.debug(f"Command stdout: {stdout_output}")
            raise PackitCommandFailedError(
                f"{error_message}",
                stdout_output=stdout_output,
                stderr_output=stderr_output,
            )
        success = False
    else:
        success = True

    if not output:
        return success

    o = stdout.get_output()
    if decode:
        return o.decode(sys.getdefaultencoding())
    else:
        return o


def run_command_remote(
    cmd,
    error_message=None,
    cwd=None,
    fail=True,
    output=False,
    env: Optional[Dict] = None,
    decode=True,
    print_live: bool = False,
):
    """
    wrapper for run_command method
    Indicating that this command run some action without local effect,
    or the effect is not important.

    eg.
        submit something to some server, and check how server reply
        call kinit of some ticket
    """
    return run_command(
        cmd, error_message, cwd, fail, output, env, decode=decode, print_live=print_live
    )


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
        logger.debug(f"Logging set to {logging.getLevelName(level)}")

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
def cwd(target: Union[str, Path]):
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


def get_packit_version() -> str:
    try:
        return get_distribution("packitos").version
    except DistributionNotFound:
        return "NOT_INSTALLED"
