import json
import logging
import os
import shlex
import subprocess
import tempfile

import git

logger = logging.getLogger("source_git")


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


def run_command(cmd, error_message=None, cwd=None, fail=True, output=False):
    if not isinstance(cmd, list):
        cmd = shlex.split(cmd)

    cwd = cwd or os.getcwd()
    error_message = error_message or cmd[0]

    shell = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=cwd,
        universal_newlines=True,
    )

    logger.debug(f"{shell.args}\n{shell.stdout}")

    if shell.returncode != 0:
        logger.error(f"{error_message}\n{shell.stderr}")
        if fail:
            raise Exception(f"{shell.args!r} failed with {error_message!r}")
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

    def __init__(self, fas_username, repo_path, directory, stage=False):
        self.fas_username = fas_username
        self.repo_path = repo_path
        self.directory = directory
        self.stage = stage

    def new_sources(self, sources="", fail=True):
        if not os.path.isdir(self.directory):
            raise Exception("Cannot access fedpkg repository:")

        return run_command(
            cmd=f"fedpkg{'-stage' if self.stage else ''} new-sources {sources}",
            cwd=self.directory,
            error_message=f"Adding new sources failed:",
            fail=fail,
        )

    def init_ticket(self, keytab):

        if keytab and os.path.isfile(keytab):
            cmd = f"kinit {self.fas_username}@FEDORAPROJECT.ORG -k -t {keytab}"
        else:
            # there is no keytab, but user still might have active ticket - try to renew it
            cmd = f"kinit -R {self.fas_username}@FEDORAPROJECT.ORG"
        return run_command(
            cmd=cmd, error_message="Failed to init kerberos ticket:", fail=True
        )


def set_logging(
        logger_name="sourcegit",
        level=logging.INFO,
        handler_class=logging.StreamHandler,
        handler_kwargs=None,
        format="%(asctime)s.%(msecs).03d %(filename)-17s %(levelname)-6s %(message)s",
        date_format="%H:%M:%S",
):
    """
    Set personal logger for this library.

    :param logger_name: str, name of the logger
    :param level: int, see logging.{DEBUG,INFO,ERROR,...}: level of logger and handler
    :param handler_class: logging.Handler instance, default is StreamHandler (/dev/stderr)
    :param handler_kwargs: dict, keyword arguments to handler's constructor
    :param format: str, formatting style
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

            formatter = logging.Formatter(format, date_format)
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
    return os.path.isdir(os.path.join(directory, ".git"))


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
        logger.debug("Source git repo exists.")
        repo = git.repo.Repo(directory)
    else:
        logger.info(f"Cloning source-git repo: {url} -> {directory}")
        repo = git.repo.Repo.clone_from(url=url, to_path=directory, tags=True)

    return repo
