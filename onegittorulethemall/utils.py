import datetime
import logging
import os
import subprocess
import tempfile
from urllib.parse import urlparse

from time import sleep

from onegittorulethemall.constant import CLONE_TIMEOUT

logger = logging.getLogger(__name__)


def parse_git_repo(potential_url):
    """Cover the following variety of URL forms for Github/Gitlab repo referencing.

    1) www.domain.com/foo/bar
    2) (same as above, but with ".git" in the end)
    3) (same as the two above, but without "www.")
    # all of the three above, but starting with "http://", "https://", "git://", "git+https://"
    4) git@domain.com:foo/bar
    5) (same as above, but with ".git" in the end)
    6) (same as the two above but with "ssh://" in front or with "git+ssh" instead of "git")

    Returns a tuple (<username>, <reponame>) or None if this does not seem to be a Github repo.

    Notably, the repo *must* have exactly username and reponame, nothing else and nothing
    more. E.g. `github.com/<username>/<reponame>/<something>` is *not* recognized.
    """
    if not potential_url:
        return None

    # transform 4-6 to a URL-like string, so that we can handle it together with 1-3
    if "@" in potential_url:
        split = potential_url.split("@")
        if len(split) == 2:
            potential_url = "http://" + split[1]
        else:
            # more @s ?
            return None

    # make it parsable by urlparse if it doesn't contain scheme
    if not potential_url.startswith(("http://", "https://", "git://", "git+https://")):
        potential_url = "http://" + potential_url

    # urlparse should handle it now
    parsed = urlparse(potential_url)

    username = None
    if ":" in parsed.netloc:
        # e.g. domain.com:foo or domain.com:1234, where foo is username, but 1234 is port number
        split = parsed.netloc.split(":")
        if split[1] and not split[1].isnumeric():
            username = split[1]

    # path starts with '/', strip it away
    path = parsed.path.lstrip("/")

    # strip trailing '.git'
    if path.endswith(".git"):
        path = path[: -len(".git")]

    split = path.split("/")
    if username and len(split) == 1:
        # path contains only reponame, we got username earlier
        return username, path
    if not username and len(split) == 2:
        # path contains username/reponame
        return split[0], split[1]

    # all other cases
    return None


def get_username_from_git_url(url):
    """http://github.com/foo/bar.git -> foo"""
    user_repo = parse_git_repo(url)
    return user_repo[0] if user_repo else None


def get_reponame_from_git_url(url):
    """http://github.com/foo/bar.git -> bar"""
    user_repo = parse_git_repo(url)
    return user_repo[1] if user_repo else None


def strip_dot_git(url):
    """Strip trailing .git"""
    return url[: -len(".git")] if url.endswith(".git") else url


def clone_repo_and_cd_inside(repo_name, repo_ssh_url, namespace):
    os.makedirs(namespace, exist_ok=True)
    os.chdir(namespace)
    logger.debug("clone %s", repo_ssh_url)

    for _ in range(CLONE_TIMEOUT):
        proc = subprocess.Popen(["git", "clone", repo_ssh_url],
                                stderr=subprocess.PIPE)
        output = proc.stderr.read().decode()
        logger.debug("Clone exited with {} and output: {}".format(proc.returncode, output))
        if "does not exist yet" not in output:
            break
        sleep(1)
    else:
        logger.error("Clone failed.")
        raise Exception("Clone failed")

    # if the repo is already cloned, it's not an issue
    os.chdir(repo_name)


def set_upstream_remote(clone_url, ssh_url, pull_merge_name):
    logger.debug("set remote upstream to %s", clone_url)
    try:
        subprocess.check_call(["git", "remote", "add", "upstream", clone_url])
    except subprocess.CalledProcessError:
        subprocess.check_call(["git", "remote", "set-url", "upstream", clone_url])
    try:
        subprocess.check_call(["git", "remote", "add", "upstream-w", ssh_url])
    except subprocess.CalledProcessError:
        subprocess.check_call(["git", "remote", "set-url", "upstream-w", ssh_url])
    logger.debug("adding fetch rule to get PRs for upstream")
    subprocess.check_call(["git", "config", "--local", "--add", "remote.upstream.fetch",
                           "+refs/{}/*/head:refs/remotes/upstream/{}r/*".format(pull_merge_name,
                                                                                pull_merge_name[
                                                                                    0])])


def set_origin_remote(ssh_url, pull_merge_name):
    logger.debug("set remote origin to %s", ssh_url)
    subprocess.check_call(["git", "remote", "set-url", "origin", ssh_url])
    logger.debug("adding fetch rule to get PRs for origin")
    subprocess.check_call(["git", "config", "--local", "--add", "remote.origin.fetch",
                           "+refs/{}/*/head:refs/remotes/origin/{}r/*".format(pull_merge_name,
                                                                              pull_merge_name[0])])


def fetch_all():
    logger.debug("fetching everything")
    with open("/dev/null", "w") as fd:
        subprocess.check_call(["git", "fetch", "--all"], stdout=fd)


def get_remote_url(remote):
    logger.debug("get remote URL for remote %s", remote)
    try:
        url = subprocess.check_output(["git", "remote", "get-url", remote])
    except subprocess.CalledProcessError:
        remote = "origin"
        logger.warning("falling back to %s", remote)
        url = subprocess.check_output(["git", "remote", "get-url", remote])
    return remote, url.decode("utf-8").strip()


def prompt_for_pr_content(commit_msgs):
    t = tempfile.NamedTemporaryFile(delete=False, prefix='gh.')
    try:
        template = "Title of this PR\n\n{}\n\n".format(commit_msgs)
        template_b = template.encode("utf-8")
        t.write(template_b)
        t.flush()
        t.close()
        try:
            editor_cmdstring = os.environ['EDITOR']
        except KeyError:
            logger.warning("EDITOR environment variable is not set")
            editor_cmdstring = "/bin/vi"

        logger.debug('using editor: %s', editor_cmdstring)

        cmd = [editor_cmdstring, t.name]

        logger.debug('invoking editor: %s', cmd)
        proc = subprocess.Popen(cmd)
        ret = proc.wait()
        logger.debug('editor returned : %s', ret)
        if ret:
            raise RuntimeError("error from editor")
        with open(t.name) as fd:
            pr_content = fd.read()
        if template == pr_content:
            logger.error("PR description is unchanged")
            raise RuntimeError("The template is not changed, the PR won't be created.")
    finally:
        os.unlink(t.name)
    logger.debug('got: %s', pr_content)
    title, body = pr_content.split("\n", 1)
    logger.debug('title: %s', title)
    logger.debug('body: %s', body)
    return title, body.strip()


def list_local_branches():
    """ return a list of dicts """
    fmt = "%(refname:short);%(upstream:short);%(authordate:iso-strict);%(upstream:track)"
    for_each_ref = subprocess.check_output(
        ["git", "for-each-ref", "--format", fmt, "refs/heads/"]
    ).decode("utf-8").strip().split("\n")
    response = []
    was_merged = subprocess.check_output(
        ["git", "branch", "--merged", "master", "--format", "%(refname:short)"]
    ).decode("utf-8").strip().split("\n")
    for li in for_each_ref:
        fields = li.split(";")
        response.append({
            "name": fields[0],
            "remote_tracking": fields[1],
            "date": datetime.datetime.strptime(fields[2][:-6], "%Y-%m-%dT%H:%M:%S"),
            "tracking_status": fields[3],
            "merged": "merged" if fields[0] in was_merged else "",
        })
    return response


def get_current_branch_name():
    return subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode("utf-8").strip()


def get_commit_msgs(branch):
    return subprocess.check_output(
        ["git", "log", "--pretty=format:- %s.",
         "%s..HEAD" % branch]).decode("utf-8").strip()


def git_push():
    """ perform `git push` """
    # it would make sense to do `git push -u`
    # this command NEEDS to be configurable
    subprocess.check_call(["git", "push", "-q"])
