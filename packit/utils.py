import json
import logging
import shlex
import subprocess
import tempfile
from pathlib import Path

import git

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
            except json.JSONDecodeError as ex:
                result[key] = raw_val
    return result


# TODO: we should use run_cmd from conu
def run_command(cmd, error_message=None, cwd=None, fail=True, output=False):
    logger.debug("cmd = %s", cmd)
    if not isinstance(cmd, list):
        logger.debug("cmd = '%s'", " ".join(cmd))
        cmd = shlex.split(cmd)

    cwd = cwd or str(Path.cwd())
    error_message = error_message or cmd[0]

    shell = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=cwd,
        universal_newlines=True,
    )

    if not output:
        # output is returned, let the caller process it
        logger.debug("%s", shell.stdout)
    logger.error("%s", shell.stderr)

    if shell.returncode != 0:
        logger.error("Command %s failed", shell.args)
        logger.error("%s", error_message)
        if fail:
            raise PackitException(f"Command {shell.args!r} failed.")
        success = False
    else:
        success = True

    if not output:
        return success

    return shell.stdout


class FedPKG:
    """
    Part of the code is from release-bot:

    https://github.com/user-cont/release-bot/blob/master/release_bot/fedora.py
    """

    def __init__(self, fas_username:str = None, directory: str = None, stage: bool = False):
        self.fas_username = fas_username
        self.directory = directory
        self.stage = stage
        if stage:
            self.fedpkg_exec = "fedpkg-stage"
        else:
            self.fedpkg_exec = "fedpkg"

    def new_sources(self, sources="", fail=True):
        if not Path(self.directory).is_dir():
            raise Exception("Cannot access fedpkg repository:")

        return run_command(
            cmd=[self.fedpkg_exec, "new-sources", sources],
            cwd=self.directory,
            error_message=f"Adding new sources failed:",
            fail=fail,
        )

    def build(self, scratch: bool = False):
        cmd = [self.fedpkg_exec, "build", "--nowait"]
        if scratch:
            cmd.append("--scratch")
        out = run_command(
            cmd=cmd,
            cwd=self.directory,
            error_message="Submission of build to koji failed.",
            fail=True,
            output=True
        )
        logger.info("%s", out)

    def init_ticket(self, keytab: str = None):
        # TODO: this method has nothing to do with fedpkg, pull it out
        if not keytab:
            logger.info("won't be doing kinit, no credentials provided")
            return
        if keytab and Path(keytab).is_file():
            cmd = ["kinit", f"{self.fas_username}@FEDORAPROJECT.ORG", "-k", "-t", keytab]
        else:
            # there is no keytab, but user still might have active ticket - try to renew it
            cmd = ["kinit", "-R", f"{self.fas_username}@FEDORAPROJECT.ORG"]
        return run_command(
            cmd=cmd, error_message="Failed to init kerberos ticket:", fail=True
        )


class PackitFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            self._style._fmt = "%(message)s"
        elif record.levelno > logging.INFO:
            self._style._fmt = "%(levelname)-8s %(message)s"
        else:  # debug
            self._style._fmt = "%(asctime)s.%(msecs).03d %(filename)-17s %(levelname)-6s %(message)s"
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


def exclude_from_dict(raw_dict: dict, *args: str):
    result = []
    for arg in args:
        if arg in raw_dict:
            result.append(raw_dict[arg])
            del raw_dict[arg]
        else:
            result.append(None)
    result.append(raw_dict)
    return result


def is_git_repo(directory: str) -> bool:
    """
    Test, if the directory is a git repo.
    (Has .git subdirectory?)
    """
    return Path(directory).joinpath(".git").is_dir()


def checkout_pr(repo: git.Repo, pr_id: int):
    """
    Checkout the branch for the pr.

    TODO: Move this to ogr and make it compatible with other git forges.
    """
    repo.remote().fetch(refspec=f"pull/{pr_id}/head:pull/{pr_id}")
    repo.refs[f"pull/{pr_id}"].checkout()


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
        logger.info(f"Cloning repo: {url} -> {directory}")
        repo = git.repo.Repo.clone_from(url=url, to_path=directory, tags=True)

    return repo
