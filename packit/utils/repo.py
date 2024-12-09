# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import re
import subprocess
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union

import git
import yaml
from git.exc import GitCommandError
from ogr.parsing import RepoUrl, parse_git_repo

from packit.constants import COMMIT_ACTION_DIVIDER
from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


class RepositoryCache:
    """
    Cache for git repositories base on the reference option of `git clone`.

    * The cache is located in the specified directory
      and contains separate git repository for each project.
    * Project name is used to match the git project in the cache.
    """

    def __init__(self, cache_path: Union[str, Path], add_new=False) -> None:
        self.cache_path = (
            Path(cache_path) if isinstance(cache_path, str) else cache_path
        )
        self.add_new = add_new
        logger.debug(
            f"Instantiation of the repository cache at {self.cache_path}. "
            f"New projects will {'not ' if not self.add_new else ''}be added.",
        )
        self.projects_added: list[str] = []
        self.projects_cloned_using_cache: list[str] = []

    @property
    def cached_projects(self) -> list[str]:
        """Project names we have in the cache."""
        if not self.cache_path.is_dir():
            self.cache_path.mkdir(parents=True)
        return [f.name for f in self.cache_path.iterdir() if f.is_dir()]

    def _clone(self, **kwargs) -> git.Repo:
        """Wrapper around git function so we are able to check the call in tests more easily."""
        return git.repo.Repo.clone_from(**kwargs)

    def get_repo(
        self,
        url: str,
        directory: Union[Path, str, None] = None,
    ) -> git.Repo:
        """
        Clone the repository.
        * If we have this repository in a cache, use the cached repo as a reference when cloning.
        * If we don't have this repository in a cache and {add_new} is True,
          clone the repository to cache first and then use it as a reference.

        :param url: will be used to clone the repo
        :param directory: target path for cloning the repository
        :return: cloned repository
        """
        directory = str(directory) if directory else tempfile.mkdtemp()

        if is_git_repo(directory=directory):
            logger.debug(f"Repo already exists in {directory}.")
            return git.repo.Repo(directory)

        logger.debug(
            f"Cloning repo {url} -> {directory} using repository cache at {self.cache_path}",
        )
        cached_projects = self.cached_projects
        cached_projects_str = "\n".join(f"- {project}" for project in cached_projects)
        logger.debug(
            f"Repositories in the cache ({len(cached_projects)} "
            f"project(s)):\n{cached_projects_str}",
        )

        project_name = RepoUrl.parse(url).repo
        reference_repo = self.cache_path.joinpath(project_name)
        if project_name not in cached_projects and self.add_new:
            logger.debug(f"Creating reference repo: {reference_repo}")
            self._clone(url=url, to_path=str(reference_repo), tags=True)
            self.projects_added.append(project_name)

        if self.add_new or project_name in cached_projects:
            logger.debug(f"Using reference repo: {reference_repo}")
            self.projects_cloned_using_cache.append(project_name)
            return self._clone(
                url=url,
                to_path=directory,
                tags=True,
                reference=str(reference_repo),
            )

        return self._clone(url=url, to_path=directory, tags=True)


def is_git_repo(directory: Union[Path, str]) -> bool:
    """
    Test, if the directory is a git repo.
    (Has .git subdirectory or 'gitdir' file?)
    """
    return Path(directory, ".git").exists()


def get_repo(url: str, directory: Optional[Union[Path, str]] = None) -> git.Repo:
    """
    Use directory as a git repo or clone repo to the tempdir.
    """
    directory = str(directory) if directory else tempfile.mkdtemp()

    if is_git_repo(directory=directory):
        logger.debug(f"Repo already exists in {directory}.")
        return git.repo.Repo(directory)
    logger.info(f"Cloning repo {url} -> {directory}")
    return git.repo.Repo.clone_from(url=url, to_path=directory, tags=True)


def get_namespace_and_repo_name(url: str) -> tuple[Optional[str], str]:
    parsed_git_repo = parse_git_repo(url)
    if parsed_git_repo is None or not parsed_git_repo.repo:
        raise PackitException(
            f"Invalid URL format, can't obtain namespace and repository name: {url}",
        )
    return parsed_git_repo.namespace, parsed_git_repo.repo


def is_a_git_ref(repo: git.Repo, ref: str) -> bool:
    try:
        commit = repo.commit(ref)
        return bool(commit)
    except git.BadName:
        return False


def get_default_branch(repository: git.Repo) -> str:
    """
    Returns default branch for newly created repos in the parent directory of
    passed in repository. Accepts `repository` to ensure the closest override of
    git configuration is used.

    Args:
        repository (git.Repo): Git repository closest to the directory where
            the configuration is applied.

    Returns:
        Default branch for new repos, if not supported or not configured returns
        `master`.
    """
    config = repository.config_reader()
    return config.get_value("init", "defaultBranch", "master")


def git_remote_url_to_https_url(
    inp: str,
    with_dot_git_suffix: Optional[bool] = True,
) -> str:
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
        if inp.endswith(".git"):
            return inp if with_dot_git_suffix else inp[:-4]

        return inp

    optional_suffix = ".git" if inp.endswith(".git") and with_dot_git_suffix else ""
    url_str = f"https://{parsed_repo.hostname}/{parsed_repo.namespace}/{parsed_repo.repo}{optional_suffix}"

    logger.debug(f"URL {inp!r} turned into HTTPS {url_str!r}")
    return url_str


def get_current_version_command(
    glob_pattern: str,
    refs: Optional[str] = "tags",
) -> list[str]:
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


def create_new_repo(cwd: Path, switches: list[str]):
    subprocess.check_call(["git", "init", *switches, str(cwd)])
    # TODO: Replace with -b / --initial-branch in `git init` when possible
    if "--bare" not in switches:
        subprocess.check_call(["git", "checkout", "-b", "main"], cwd=cwd)
    else:
        subprocess.check_call(
            ["git", "symbolic-ref", "HEAD", "refs/heads/main"],
            cwd=cwd,
        )


def git_patch_ish(patch: str) -> str:
    """
    Massage patch to look like a Git-style patch, so that it can
    be passed to 'git patch-id' in order to calculate a patch-id.

    :param patch: Patch to transform.
    :return: Transformed patch.
    """
    # Prettend as if format is 'diff --git'
    pattern = re.compile(r"^diff -\w+ ", flags=re.MULTILINE)
    repl = r"diff --git "
    patch = re.sub(pattern, repl, patch)

    # Remove timestamps from comparison lines
    pattern = re.compile(r"^((---|\+\+\+) .+)\t\d{4}.+$", flags=re.MULTILINE)
    repl = r"\1"
    patch = re.sub(pattern, repl, patch)

    # Add missing 'diff --git' lines
    if "diff --git " not in patch:
        # Timestamps (see above) already need to be removed
        # for this substitution pattern to work.
        pattern = re.compile(r"(\n--- (.+)\n\+\+\+ (.+)\n)")
        repl = r"\ndiff --git \2 \3\1"
        patch = re.sub(pattern, repl, patch)

    return patch


def get_message_from_metadata(metadata: dict, header: Optional[str] = None) -> str:
    if not isinstance(metadata, dict):
        raise PackitException(
            f"We can save only dictionaries to metadata. Not {metadata}",
        )

    content = (
        yaml.dump(metadata, indent=4, default_flow_style=False) if metadata else ""
    )
    if not header:
        return content

    return f"{header}\n\n{content}"


def get_metadata_from_message(commit: git.Commit) -> Optional[dict]:
    """
    Tries to load yaml format from the git message.

    We are skipping first line until
    the rest of the content is yaml-loaded to dictionary (yaml object type).

    If nothing found, we return None.

    Reference:
    https://gitpython.readthedocs.io/en/stable/reference.html
    ?highlight=archive#module-git.objects.commit

    e.g.:

    I)
    key: value
    another: value
    -> {"key": "value", "another": "value"}

    II)
    On sentence.

    key: value
    another: value
    -> {"key": "value", "another": "value"}

    III)
    A lot of
    text

    before keys.

    key: value
    another: value
    -> {"key": "value", "another": "value"}

    IV)
    Other values are supported as well:

    key:
    - first
    - second
    - third

    :param commit: git.Commit object
    :return: dict loaded from message if it satisfies the rules above
    """
    splitted_message = commit.message.split("\n")

    for i in range(len(splitted_message)):
        message_part = "\n".join(splitted_message[i:])
        try:
            loaded_part = yaml.safe_load(message_part)
        except yaml.YAMLError:
            continue

        if isinstance(loaded_part, dict):
            return loaded_part

    return None


def shorten_commit_hash(commit_hash: str) -> str:
    """
    Shortens commit hash to first 8 characters.

    Args:
        commit_hash: Commit hash to be shortened.

    Returns:
        First 8 characters of the commit hash.
    """
    return commit_hash[:8]


def get_next_commit(repo: git.Repo, commit: str) -> Optional[str]:
    """Returns the commit following the specified commit.

    Args:
        repo: Git repo to search the commit in.
        commit: Hash of the commit to get the next commit of.

    Returns:
        The hash of the commit following the given commit or None if no
        such commit exists, i.e. the given commit is the HEAD.
    """
    commits = list(repo.iter_commits(f"{commit}..", ancestry_path=True))
    return commits[-1].hexsha if commits else None


def commit_exists(repo: git.Repo, commit: str) -> bool:
    """Checks whether a commit with the given hash exists.

    Args:
        repo: Git repo to check if the commit exists in.
        commit: Hash of the commit to check.

    Returns:
        Whether a commit with such hash exists
    """
    try:
        list(repo.iter_commits(f"{commit}..{commit}"))
    except GitCommandError:
        return False
    else:
        return True


def get_commit_diff(commit: git.Commit) -> list[git.Diff]:
    """Get modified files of the given commit.

    Args:
        commit: Commit to get the diff of.

    Returns:
        List of git.Diff containing information about the modified files
        in the given commit.
    """
    if len(commit.parents) == 1:
        return commit.parents[0].diff(commit, create_patch=True)
    if len(commit.parents) == 0:
        # First commit in the repo
        return commit.diff(git.NULL_TREE, create_patch=True)
    # Probably a merge commit, we can't do much about it
    return []


def get_commit_hunks(repo: git.Repo, commit: git.Commit) -> list[str]:
    """Get a list of hunks of the given commit.

    Args:
        repo: Git repo which the commit belongs to.
        commit: Commit to get hunks of.

    Returns:
        List of split commit hunks stored as strings where each string
        represents changes of a single file.
    """
    patch = repo.git.show(commit, format="", color="never")
    hunk_start_re = re.compile(r"diff --git a/.+ b/.+")
    section_start = 0
    result = []
    patch_lines = patch.splitlines()
    for i, line in enumerate(patch_lines):
        if hunk_start_re.match(line):
            section = patch_lines[section_start:i]
            if section:
                result.append("\n".join(section))
            section_start = i
    # The last section
    section = patch_lines[section_start:]
    if section:
        result.append("\n".join(section))
    return result


def is_the_repo_pristine(repo: git.Repo) -> bool:
    """Checks whether the repository is pristine.

    Args:
        repo: Git repo to check.

    Returns:
        Whether the repo is pristine.
    """
    return not repo.git.diff() and not repo.git.clean("-xdn")


def get_file_author(repo: git.Repo, filename: str) -> str:
    """Get the original author of 'filename' in 'repo'

    Args:
        repo: Git-repo where the file is commited.
        filename: Name of the file.

    Returns:
        The original (first) author of the file in the
        "A U Thor <author@example.com>" format.
    """
    author, author_mail = "", ""
    for line in repo.git.blame(filename, line_porcelain=True).splitlines():
        token, _, value = line.partition(" ")
        if token == "author":
            author = value
        elif token == "author-mail":
            author_mail = value
        elif token == "filename":
            # End of the first blame-block
            break
    return f"{author} {author_mail}"


@contextmanager
def commit_message_file(
    subject: str,
    message: Optional[str] = None,
    trailers: Optional[list[tuple[str, str]]] = None,
) -> Generator[str, None, None]:
    """Context manager to yield a commit message file

    Which then can be used by a commit operation.

    This handles a few things:
    - It concatenates a commit message subject line and a message.
      Though: if 'subject' is the complete commit message that'll also work.
    - Adds the Git-trailers specified by 'trailers'.

    Args:
        subject: Subject line of the commit message.
        message: Message following the subject line.
        trailers: List Git-trailers to be added to the commit message.

    Yields:
        Name of the temporary file with the prepared commit message.
    """
    with tempfile.NamedTemporaryFile(mode="w+t") as fp:
        fp.writelines([subject, "\n"])
        if message:
            fp.writelines(["\n", message, "\n"])
        fp.seek(0)
        if trailers:
            args = ["--in-place", "--if-exists", "replace"]
            for token, value in trailers:
                args += ["--trailer", f"{token}={value}"]
            # 'interpret-trailers' doesn't require a working directory,
            # so a plain Git command can be used here.
            git.cmd.Git().interpret_trailers(*args, fp.name)
        yield fp.name


def get_commit_message_from_action(
    output: Optional[list[str]],
    default_title: str,
    default_description: str,
) -> tuple[str, str]:
    """
    Parse the output of the commit action and in case the action is not defined,
    no output has been produced or it couldn't be parsed, return the defaults.

    Args:
        output: Output produced by the `commit-message` action.
        default_title: Commit title that is used in case the produced commit
            message hasn't been produced, is malformed or couldn't be parsed.
        default_description: Commit description that is used in case the
            produced commit message hasn't been produced, is malformed or
            couldn't be parsed.

    Returns:
        Pair of the commit title and commit message that will be used.
    """
    # no output has been produced, or action doesn't exist
    if not output:
        return (default_title, default_description)

    # split by the divider
    split_output = "".join(output).rsplit(sep=COMMIT_ACTION_DIVIDER, maxsplit=1)

    # -1 ensures we're taking just the message, ignoring, if any, debugging
    # output
    whole_message = split_output[-1]

    # we split only once, cause we separate the commit title
    split_commit_message = whole_message.split("\n\n", maxsplit=1)

    # nothing found or empty title
    if len(split_commit_message) < 1 or not split_commit_message[0]:
        return default_title, default_description

    title = split_commit_message[0]
    description = split_commit_message[1] if len(split_commit_message) > 1 else ""

    # it is later reconstructed in a generic way for both defaults and override,
    # so we don't care about the whitespace at the beginning and the end
    return title.strip(), description.strip()


def get_tag_link(git_url: str, upstream_tag: str) -> str:
    """
    Get link to the tag of a Git repo.
    """
    link = ""
    git_repo = parse_git_repo(git_url)
    if not git_repo:
        return ""

    forge = git_repo.hostname
    if not forge:
        return ""

    if forge == "github.com":
        link = f"{git_url}/releases/tag/{upstream_tag}"
    # GitLab or GitLab instances (e.g. gitlab.gnome.org)
    elif "gitlab" in forge:
        link = f"{git_url}/-/tags/{upstream_tag}"

    return link


def get_commit_link(git_url: str, upstream_commit: str) -> str:
    """
    Get link to the commit of a Git repo.
    """
    link = ""
    git_repo = parse_git_repo(git_url)
    if not git_repo:
        return ""

    forge = git_repo.hostname
    if not forge:
        return ""

    if forge == "github.com":
        link = f"{git_url}/commit/{upstream_commit}"
    # GitLab or GitLab instances (e.g. gitlab.gnome.org)
    elif "gitlab" in forge:
        link = f"{git_url}/-/commit/{upstream_commit}"
    elif forge == "pagure.io":
        link = f"{git_url}/c/{upstream_commit}"

    return link
