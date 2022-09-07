#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import re
from typing import List, Optional

import click
from git import Commit, Repo

NOT_IMPORTANT_VALUES = ["n/a", "none", "none.", ""]
RELEASE_NOTES_TAG = "RELEASE NOTES"
RELEASE_NOTES_RE = f"{RELEASE_NOTES_TAG} BEGIN\n(.+)\n{RELEASE_NOTES_TAG} END"
PRE_COMMIT_CI_MESSAGE = "pre-commit autoupdate"


def get_relevant_commits(repository: Repo, ref: Optional[str] = None) -> List[Commit]:
    if not ref:
        tags = sorted(repository.tags, key=lambda t: t.commit.committed_datetime)
        if not tags:
            raise click.UsageError(
                "No REF was specified and the repo contains no tags, "
                "the REF must be specified manually."
            )
        ref = tags[-1]
    range = f"{ref}..HEAD"
    return list(repository.iter_commits(rev=range, merges=True))


def get_pr_data(message: str, repo: Optional[str] = None) -> str:
    """
    obtain PR ID and produce a markdown link to it

    if repo is set, creates a markdown link to the given repo (useful for blogposts)
    """
    # Merge pull request #1483 from majamassarini/fix/1357
    first_line = message.split("\n")[0]
    fourth_word = first_line.split(" ")[3]
    if repo:
        pr_id = fourth_word.lstrip("#")
        url = f"https://github.com/packit/{repo}/pull/{pr_id}"
        return f"[{repo}#{pr_id}]({url})"
    else:
        return fourth_word


def convert_message(message: str) -> Optional[str]:
    """Extract release note from the commit message,
    return None if there is no release note"""
    if RELEASE_NOTES_TAG in message:
        # new
        if match := re.findall(RELEASE_NOTES_RE, message, re.DOTALL):
            return match[0]
        else:
            return None
    return None


def get_changelog(commits: List[Commit], repo: Optional[str] = None) -> str:
    changelog = ""
    for commit in commits:
        if PRE_COMMIT_CI_MESSAGE in commit.message:
            continue
        message = convert_message(commit.message)
        if message and message.lower() not in NOT_IMPORTANT_VALUES:
            suffix = get_pr_data(commit.message, repo)
            changelog += f"- {message} ({suffix})\n"
    return changelog


@click.command(
    short_help="Get the changelog from the merge commits",
    help="""Get the changelog from the merge commits

    The script goes through the merge commits since the specified REF
    and gets the changelog entry from the commit message.
    In case no REF is specified, the latest tag is used.

    Currently, the changelog entry in the message is detected based on
    explicit marks of the beginning and the end denoted by
    `RELEASE NOTES BEGIN` and `RELEASE NOTES END` separators.
    """,
)
@click.option(
    "--git-repo",
    default=".",
    type=click.Path(dir_okay=True, file_okay=False),
    help="Git repository used for getting the changelog. "
    "Current directory is used by default.",
)
@click.argument("ref", type=click.STRING, required=False)
def changelog(git_repo, ref):
    print(get_changelog(get_relevant_commits(Repo(git_repo), ref)))


if __name__ == "__main__":
    changelog()
