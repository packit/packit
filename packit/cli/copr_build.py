# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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
import logging
import os
from typing import Optional, List

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings, PackageConfig
from packit.config.aliases import get_valid_build_targets
from packit.utils import sanitize_branch_name

logger = logging.getLogger(__name__)


@click.command("copr-build", context_settings=get_context_settings())
@click.option("--nowait", is_flag=True, default=False, help="Don't wait for build")
@click.option(
    "--owner",
    help="Copr user, owner of the project. (defaults to username from copr config)",
)
@click.option(
    "--project",
    help="Project name to build in. Will be created if does not exist. "
    "(defaults to the first found project value in the config file or "
    "'packit-cli-{repo_name}-{branch/commit}')",
)
@click.option(
    "--targets",
    help="Comma separated list of chroots to build in. (defaults to 'fedora-rawhide-x86_64')",
    default="fedora-rawhide-x86_64",
)
@click.option(
    "--description", help="Description of the project to build in.", default=None
)
@click.option(
    "--instructions",
    help="Installation instructions for the project to build in.",
    default=None,
)
@click.option(
    "--list-on-homepage",
    help="Created copr project will be visible on copr's home-page.",
    default=False,
    is_flag=True,
)
@click.option(
    "--preserve-project",
    help="Created copr project will not be removed after 60 days.",
    default=False,
    is_flag=True,
)
@click.option(
    "--additional-repos",
    help="URLs to additional yum repos, which can be used during build. "
    "Comma separated. "
    "This should be baseurl from .repo file. "
    "E.g.: http://copr-be.cloud.fedoraproject.org/"
    "results/rhughes/f20-gnome-3-12/fedora-$releasever-$basearch/",
    default=None,
)
@click.option(
    "--upstream-ref",
    default=None,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
)
@click.option(
    "--request-admin-if-needed",
    help="Ask for admin permissions when we need to change settings of the copr project "
    "and are not allowed to do so.",
    default=False,
    is_flag=True,
)
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@pass_config
@cover_packit_exception
def copr_build(
    config,
    nowait,
    owner,
    project,
    targets,
    description,
    instructions,
    list_on_homepage,
    preserve_project,
    upstream_ref,
    additional_repos,
    request_admin_if_needed,
    path_or_url,
):
    """
    Build selected upstream project in COPR.

    PATH_OR_URL argument is a local path or a URL to the upstream git repository,
    it defaults to the current working directory.
    """
    api = get_packit_api(config=config, local_project=path_or_url)
    if not project:
        logger.debug("COPR project name was not passed via CLI.")

        if isinstance(api.package_config, PackageConfig):
            project = api.package_config.get_copr_build_project_value()

        if project:
            logger.debug("Using a first COPR project found in the job configuration.")
        else:
            logger.debug(
                "COPR project not found in the job configuration. "
                "Using the default one."
            )
            sanitized_ref = sanitize_branch_name(path_or_url.ref)
            project = f"packit-cli-{path_or_url.repo_name}-{sanitized_ref}"

    logger.info(f"Using COPR project name = {project}")

    targets_to_build = get_valid_build_targets(
        *targets.split(","), default="fedora-rawhide-x86_64"
    )

    logger.info(f"Targets to build: {targets_to_build}.")

    additional_repos_list: Optional[List[str]] = (
        additional_repos.split(",") if additional_repos else None
    )

    build_id, repo_url = api.run_copr_build(
        project=project,
        chroots=list(targets_to_build),
        owner=owner,
        description=description,
        instructions=instructions,
        upstream_ref=upstream_ref,
        list_on_homepage=list_on_homepage,
        preserve_project=preserve_project,
        additional_repos=additional_repos_list,
        request_admin_if_needed=request_admin_if_needed,
    )
    click.echo(f"Build id: {build_id}, repo url: {repo_url}")
    if not nowait:
        api.watch_copr_build(build_id=build_id, timeout=60 * 60 * 2)
