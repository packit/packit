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

from packit.cli.utils import cover_packit_exception
from packit.config import pass_config, get_context_settings

logger = logging.getLogger(__file__)


@click.command("srpm", context_settings=get_context_settings())
@click.option("--dest-dir")
@click.option("--upstream-ref")
@click.option("--version")
@click.argument("repo", default=os.path.abspath(os.path.curdir))
@pass_config
@cover_packit_exception
def sg2srpm(config, dest_dir, upstream_ref, version, repo):
    """
    Generate a srpm from packit.

    This script is meant to accept a source git repo with a branch as an input and produce a SRPM.

    It is expected to do this:

    1. clone the repo

    2. create archive out of the sources

    3. create SRPM
    """
    """
    package_config = get_local_package_config(try_local_dir_first=True)
    sourcegit = LocalProject(git_url=repo)
    if not package_config:
        package_config = get_local_package_config(sourcegit.working_dir)

    distgit = LocalProject(
        git_url=package_config.metadata["dist_git_url"],
        namespace="rpms",
        repo_name=package_config.metadata["package_name"],
        working_dir=dest_dir,
    )

    distgit.working_dir_temporary = False
    with Transformator(
        sourcegit=sourcegit,
        distgit=distgit,
        version=version,
        fas_username=config.fas_user,
        package_config=package_config,
    ) as t:
        t.download_upstream_archive()
        t.copy_synced_content_to_distgit_directory(
            synced_files=package_config.synced_files
        )
        patches = t.create_patches(upstream=upstream_ref)
        t.add_patches_to_specfile(patch_list=patches)
        srpm = t.create_srpm()
        click.echo(srpm)
    """
