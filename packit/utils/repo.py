# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Optional, Union, List

import git
import yaml

from ogr.parsing import RepoUrl, parse_git_repo
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
            f"New projects will {'not ' if not self.add_new else ''}be added."
        )

    @property
    def cached_projects(self) -> List[str]:
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
        directory: Union[Path, str] = None,
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
            f"Cloning repo {url} -> {directory} using repository cache at {self.cache_path}"
        )
        cached_projects = self.cached_projects
        cached_projects_str = "\n".join(f"- {project}" for project in cached_projects)
        logger.debug(
            f"Repositories in the cache ({len(cached_projects)} project(s)):\n{cached_projects_str}"
        )

        project_name = RepoUrl.parse(url).repo
        reference_repo = self.cache_path.joinpath(project_name)
        if project_name not in cached_projects and self.add_new:
            logger.debug(f"Creating reference repo: {reference_repo}")
            self._clone(url=url, to_path=str(reference_repo), tags=True)

        if self.add_new or project_name in cached_projects:
            logger.debug(f"Using reference repo: {reference_repo}")
            return self._clone(
                url=url, to_path=directory, tags=True, reference=str(reference_repo)
            )

        return self._clone(url=url, to_path=directory, tags=True)


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


def create_new_repo(cwd: Path, switches: List[str]):
    subprocess.check_call(["git", "init"] + switches + [str(cwd)])
    # TODO: Replace with -b / --initial-branch in `git init` when possible
    if "--bare" not in switches:
        subprocess.check_call(["git", "checkout", "-b", "main"], cwd=cwd)
    else:
        subprocess.check_call(
            ["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=cwd
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
            f"We can save only dictionaries to metadata. Not {metadata}"
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
