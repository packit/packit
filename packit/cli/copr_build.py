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
import logging
import os

import click

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api
from packit.config import pass_config, get_context_settings, PackageConfig
from packit.config.aliases import get_build_targets

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
    "--upstream-ref",
    default=None,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
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
    upstream_ref,
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
        project = f"packit-cli-{path_or_url.repo_name}-{path_or_url.ref}"
        if isinstance(api.package_config, PackageConfig):
            project = api.package_config.get_copr_build_project_value()
            logger.info(f"Using COPR project name = {project}")

    targets_to_build = get_build_targets(
        *targets.split(","), default="fedora-rawhide-x86_64"
    )

    build_id, repo_url = api.run_copr_build(
        project=project,
        chroots=list(targets_to_build),
        owner=owner,
        description=description,
        instructions=instructions,
        upstream_ref=upstream_ref,
    )
    click.echo(f"Build id: {build_id}, repo url: {repo_url}")
    if not nowait:
        api.watch_copr_build(build_id=build_id, timeout=60 * 60 * 2)
