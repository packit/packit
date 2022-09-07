#!/usr/bin/python3

import click
from typing import List
from pathlib import Path

from git import Repo
from changelog import get_changelog, get_relevant_commits
from specfile import Specfile


@click.command()
@click.argument("version")
@click.argument("specfile_path", nargs=-1, type=click.Path(exists=True, dir_okay=False))
def prepare_release(version: str, specfile_path: List[str]):
    new_entry = get_changelog(get_relevant_commits(Repo()))
    changelog_file = Path("CHANGELOG.md")
    current_changelog = changelog_file.read_text()
    changelog_file.write_text(f"# {version}\n\n{new_entry}\n{current_changelog}")
    for path in specfile_path:
        with Specfile(path, autosave=True) as specfile:
            specfile.version = version
            specfile.release = "1"
            specfile.add_changelog_entry(f"- New upstream release {version}")


if __name__ == "__main__":
    prepare_release()
