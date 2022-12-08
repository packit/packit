# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings
from packit.config.aliases import get_branches
from packit.constants import DEFAULT_BODHI_NOTE
from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


class BugzillaIDs(click.ParamType):
    name = "bugzilla_ids"

    def convert(self, value, param, ctx):
        ids = []

        str_ids = value.split(",")
        for bugzilla_id in str_ids:
            try:
                ids.append(int(bugzilla_id))
            except ValueError:
                raise click.BadParameter(
                    "cannot parse non-integer bugzilla ID. Please use following "
                    "format: id[,id]"
                )

        return ids


@click.command("create-update", context_settings=get_context_settings())
@click.option(
    "--dist-git-branch",
    help="Comma separated list of target branches in dist-git to create bodhi update in. "
    "(defaults to repo's default branch)",
)
@click.option(
    "--dist-git-path",
    help="Path to dist-git repo to work in. "
    "Otherwise clone the repo in a temporary directory.",
)
@click.option(
    "--koji-build",
    help="Koji build (NVR) to add to the bodhi update (can be specified multiple times)",
    required=False,
    multiple=True,
)
# It would make sense to open an editor here,
# just like `git commit` and get notes like that
@click.option(
    "--update-notes",
    help="Bodhi update notes",
    required=False,
    default=DEFAULT_BODHI_NOTE,
)
@click.option(
    "--update-type",
    type=click.types.Choice(("security", "bugfix", "enhancement", "newpackage")),
    help="Type of the bodhi update",
    required=False,
    default="enhancement",
)
@click.option(
    "-b",
    "--resolve-bugzillas",
    help="Bugzilla IDs that are resolved with the update",
    required=False,
    default=None,
    type=BugzillaIDs(),
)
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@pass_config
@cover_packit_exception
def create_update(
    config,
    dist_git_branch,
    dist_git_path,
    koji_build,
    update_notes,
    update_type,
    resolve_bugzillas,
    path_or_url,
):
    """
    Create a bodhi update for the selected upstream project

    If you are not authenticated with the bodhi server, please make sure that you
    navigate in your browser to the URL provided by the bodhi-client and then paste
    the `code=XX...` to the terminal when prompted.

    If you set `fas_user` and `kerberos_realm` in your "~/.config/packit.yaml" and
    have an active Kerberos TGT, you will be automatically authenticated. Otherwise,
    you need to follow the prompt

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory
    """
    api = get_packit_api(
        config=config, dist_git_path=dist_git_path, local_project=path_or_url
    )
    default_dg_branch = api.dg.local_project.git_project.default_branch
    dist_git_branch = dist_git_branch or default_dg_branch
    branches_to_update = get_branches(
        *dist_git_branch.split(","), default_dg_branch=default_dg_branch
    )
    click.echo(
        f"Creating Bodhi update for the following branches: {', '.join(branches_to_update)}"
    )

    if branches_to_update:
        click.echo("Please provide Bodhi username and password when asked for.")

    for branch in branches_to_update:
        try:
            api.create_update(
                koji_builds=koji_build,
                dist_git_branch=branch,
                update_notes=update_notes,
                update_type=update_type,
                bugzilla_ids=resolve_bugzillas,
            )
        except PackitException as ex:
            click.echo(
                f"There was a problem while creating an update for {branch}:\n{ex}\n\n"
                "Please try again later if this looks like a transient issue.\n"
                "If you believe this is a bug, please contact Fedora infrastructure:\n"
                "  https://pagure.io/fedora-infrastructure\n\n"
                "You are always welcome to contact the Packit team:\n"
                "  https://github.com/packit/packit/issues",
                err=True,
            )
            return
