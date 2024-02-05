# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Generate initial dist-git configuration for packit's release syncing
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import click
import yaml
from yaml import safe_load

from packit.api import PackitAPI
from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_existing_config
from packit.config import PackageConfig, get_context_settings
from packit.config.config import Config, pass_config
from packit.distgit import DistGit
from packit.exceptions import PackitException

logger = logging.getLogger(__name__)

ONBOARD_BRANCH_NAME = "packit-config"

CONFIG_FILE_NAME = ".packit.yaml"
CONFIG_HEADER = """# See the documentation for more information:
# https://packit.dev/docs/configuration/
"""

COMMIT_MESSAGE = """Add Packit configuration for automating release syncing"""
PR_DESCRIPTION = """
For more details, see https://packit.dev/docs/configuration/ or contact
[the Packit team](https://packit.dev#contacts).

"""


@click.command("init", context_settings=get_context_settings())
@click.option(
    "--upstream-git-url",
    help="URL to the upstream GIT repository",
    required=True,
)
@click.option(
    "--upstream-tag-template",
    help="Template applied for upstream tags if they differ from versions. E.g. 'v{version}' ",
)
@click.option(
    "--upstream-tag-include",
    help="Python regex used for filtering upstream tags to include. ",
)
@click.option(
    "--upstream-tag-exclude",
    help="Python regex used for filtering upstream tags to exclude. ",
)
@click.option(
    "--issue-repository",
    help="URL of a git repository that can be used for reporting errors in form of issues. ",
)
@click.option(
    "--no-pull",
    default=False,
    is_flag=True,
    help="Do not include the pull from upstream job in the config",
)
@click.option(
    "--no-koji-build",
    default=False,
    is_flag=True,
    help="Do not include the Koji build job in the config",
)
@click.option(
    "--allowed-committers",
    help="Comma separated list of allowed_committers used for Koji builds",
    default="",
)
@click.option(
    "--allowed-pr-authors",
    help="Comma separated list of allowed_pr_authors used for Koji builds",
    default="",
)
@click.option(
    "--no-bodhi-update",
    default=False,
    is_flag=True,
    help="Do not include the Bodhi update job in the config",
)
@click.option(
    "--actions-file",
    help="Yaml file with 'actions' that should be used for the config",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--dist-git-branches",
    help="Comma separated list of target branches in dist-git to release into. "
    "(defaults to rawhide)",
)
@click.option(
    "--push-to-distgit",
    "-p",
    default=False,
    is_flag=True,
    help="Push the generated Packit config to the dist-git repository's rawhide",
)
@click.option(
    "--create-pr",
    "-c",
    default=False,
    is_flag=True,
    help="Create a PR with generated Packit config",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Reset config to default if already exists.",
)
@click.option(
    "--clone-path",
    help="Path to clone the dist-git repo into (if path_or_url is URL). "
    "Otherwise clone the repo in a temporary directory.",
)
@click.option(
    "--commit-msg",
    help="Commit message used when creating a PR (also for the title) or pushing to dist-git. "
    f"Default: {COMMIT_MESSAGE!r}",
)
@click.argument(
    "path_or_url",
    type=LocalProjectParameter(),
    default=os.path.curdir,
)
@pass_config
@cover_packit_exception
def init(
    config,
    upstream_git_url,
    upstream_tag_template,
    upstream_tag_include,
    upstream_tag_exclude,
    issue_repository,
    no_pull,
    no_koji_build,
    allowed_committers,
    allowed_pr_authors,
    no_bodhi_update,
    actions_file,
    dist_git_branches,
    push_to_distgit,
    create_pr,
    force,
    clone_path,
    commit_msg,
    path_or_url,
):
    """
    Create the initial Packit dist-git configuration for Fedora release syncing based on
    the input parameters.

    This command adds `.packit.yaml` file to the dist-git repository either:

    \b 1. specified by path (defaults to current working directory)

    \b 2. specified by URL (`https://src.fedoraproject.org/rpms/<package>`) - clones the repository
    and adds the config in there. Ideally use this with --clone-path option, otherwise the
    repository is cloned to a temporary directory that is then removed.

    By default, all 3 jobs (`pull_from_upstream`, `koji_build`, `bodhi_update`) for release
    syncing are configured. You can use --no-pull, --no-koji-build or --no-bodhi-update
     options to not add some of the jobs (at the moment, Bodhi updates are created only for
     Koji builds built by Packit, therefore --no-koji-build implies also no Bodhi update job).

    You can either create the Packit config file only locally (default), or create a pull request
    (using --create-pr option) or push directly to the dist-git's default branch
    (--push-to-distgit).

    See 'packit init', if you want to initialize a repository as an upstream repo.

    Examples

    Local generation for dist-git repo in current working directory:

    \b
        $ packit dist-git init --upstream-git-url https://github.com/packit/packit .


    Local generation for dist-git repo specified by URL that will be cloned to `<my-package>` dir:

    \b
        $ packit dist-git init --upstream-git-url https://github.com/packit/packit --clone-path
        `<my-package>` https://src.fedoraproject.org/rpms/packit

    """
    if no_pull and no_koji_build:
        logger.warning("At least one job needs to be defined!")
        return

    DistGitInitializer(
        upstream_git_url=upstream_git_url,
        upstream_tag_template=upstream_tag_template,
        upstream_tag_include=upstream_tag_include,
        upstream_tag_exclude=upstream_tag_exclude,
        issue_repository=issue_repository,
        no_pull=no_pull,
        no_koji_build=no_koji_build,
        no_bodhi_update=no_bodhi_update,
        allowed_committers=allowed_committers,
        allowed_pr_authors=allowed_pr_authors,
        actions_file=actions_file,
        dist_git_branches=dist_git_branches,
        create_pr=create_pr,
        push_to_distgit=push_to_distgit,
        force=force,
        config=config,
        path_or_url=path_or_url,
        commit_msg=commit_msg,
    ).initialize_dist_git()


class PackitDumper(yaml.SafeDumper):
    # to not create yaml anchors when dumping
    # https://github.com/yaml/pyyaml/issues/535#issuecomment-1293636712
    def ignore_aliases(self, data):
        return True

    # correct list indentation
    # https://github.com/yaml/pyyaml/issues/234#issuecomment-765894586
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)


class DistGitInitializer:
    def __init__(
        self,
        config: Config,
        path_or_url: LocalProjectParameter,
        upstream_git_url: str,
        upstream_tag_template: Optional[str] = None,
        upstream_tag_include: Optional[str] = None,
        upstream_tag_exclude: Optional[str] = None,
        issue_repository: Optional[str] = None,
        no_pull: bool = False,
        no_koji_build: bool = False,
        allowed_committers: Optional[str] = None,
        allowed_pr_authors: Optional[str] = None,
        no_bodhi_update: bool = False,
        actions_file: Optional[Path] = None,
        dist_git_branches: Optional[str] = None,
        push_to_distgit: bool = False,
        create_pr: bool = False,
        force: bool = False,
        commit_msg: Optional[str] = None,
    ):
        self.config = config
        self.upstream_git_url = upstream_git_url
        self.upstream_tag_template = upstream_tag_template
        self.upstream_tag_include = upstream_tag_include
        self.upstream_tag_exclude = upstream_tag_exclude
        self.issue_repository = issue_repository
        self.no_pull = no_pull
        self.no_koji_build = no_koji_build
        self.allowed_committers = (
            allowed_committers.split(",") if allowed_committers else None
        )
        self.allowed_pr_authors = (
            allowed_pr_authors.split(",") if allowed_pr_authors else None
        )
        self.no_bodhi_update = no_bodhi_update
        self.actions_file = actions_file
        self.dist_git_branches = (
            dist_git_branches.split(",") if dist_git_branches else ["fedora-rawhide"]
        )
        self.push_to_distgit = push_to_distgit
        self.create_pr = create_pr
        self.path_or_url = path_or_url
        self.force = force
        self.commit_msg = commit_msg or COMMIT_MESSAGE

    @property
    def working_dir(self):
        return self.path_or_url.working_dir

    @property
    def config_path(self):
        return self.get_or_create_config_path()

    @property
    def package_config_dict(self):
        return self.generate_package_config_dict()

    @property
    def actions(self):
        return self.parse_actions_from_file() if self.actions_file else {}

    @property
    def package_config_content(self):
        return (
            f"{CONFIG_HEADER}\n"
            f"{yaml.dump(self.package_config_dict, sort_keys=False, Dumper=PackitDumper)}"
        )

    def initialize_dist_git(self):
        logger.info(
            f"Generating config for dist-git repository placed in {self.config_path}",
        )

        logger.info(f"Generated config: \n\n{self.package_config_content}\n\n")

        if not (self.push_to_distgit or self.create_pr):
            self.write_package_config()
            return

        logger.info(
            f"About to {'push' if self.push_to_distgit else 'create PR with'} "
            f"the generated Packit config.",
        )

        self.write_and_push()

    def get_or_create_config_path(self):
        config_path = get_existing_config(self.working_dir)
        if config_path:
            if not self.force:
                raise PackitException(
                    f"Packit config {config_path} already exists."
                    " If you want to regenerate it use `--force` option",
                )
        else:
            config_path = self.working_dir / CONFIG_FILE_NAME

        return config_path

    def parse_actions_from_file(self) -> dict:
        with open(self.actions_file) as file:
            actions_content = file.read()

        try:
            actions = safe_load(actions_content)
            if not isinstance(actions, dict):
                raise ValueError("The content of the actions file is not a dictionary.")
        except Exception as e:
            raise ValueError(f"Error parsing YAML content: {e}") from e

        return actions

    def generate_package_config_dict(self):
        # TODO maybe take the URL from spec-file and check if it is a git URL?
        config: dict[str, Any] = {"upstream_project_url": self.upstream_git_url}

        optional_config_keys = [
            "upstream_tag_template",
            "upstream_tag_include",
            "upstream_tag_exclude",
            "issue_repository",
            "allowed_committers",
            "allowed_pr_authors",
            "actions",
        ]

        for key in optional_config_keys:
            value = getattr(self, key, None)
            if value:
                config[key] = value

        config["jobs"] = []
        if not self.no_pull:
            config["jobs"].append(
                {
                    "job": "pull_from_upstream",
                    "trigger": "release",
                    "dist_git_branches": self.dist_git_branches,
                },
            )
        if not self.no_koji_build:
            config["jobs"].append(
                {
                    "job": "koji_build",
                    "trigger": "commit",
                    "dist_git_branches": self.dist_git_branches,
                },
            )

        # currently it doesn't make sense to create Bodhi job
        # if Koji job is not configured
        if not self.no_koji_build and not self.no_bodhi_update:
            config["jobs"].append(
                {
                    "job": "bodhi_update",
                    "trigger": "commit",
                    # TODO we could compute the branches to exclude from Bodhi (autoupdates)
                    "dist_git_branches": self.dist_git_branches,
                },
            )

        return config

    def write_and_push(self):
        # needed for PackitAPI to work
        package_config_dict_for_api = self.package_config_dict
        package_config_dict_for_api[
            "specfile_path"
        ] = f"{self.path_or_url.repo_name}.spec"

        package_config = PackageConfig.get_from_dict(
            raw_dict=package_config_dict_for_api,
            repo_name=self.path_or_url.repo_name,
        )

        api = PackitAPI(
            config=self.config,
            package_config=package_config,
            upstream_local_project=None,
            downstream_local_project=self.path_or_url,
        )

        default_dg_branch = api.dg.local_project.git_project.default_branch

        logger.info(f"Updating the default branch {default_dg_branch!r} first.")
        api.dg.update_branch(default_dg_branch)
        api.dg.switch_branch(default_dg_branch)

        if self.create_pr:
            self.handle_pr_creation(api, default_dg_branch)
        else:
            self.handle_push(api, default_dg_branch)

    def handle_pr_creation(self, api: PackitAPI, default_dg_branch: str):
        api.dg.create_branch(ONBOARD_BRANCH_NAME)
        api.dg.switch_branch(ONBOARD_BRANCH_NAME)
        self.write_package_config()
        self.commit_config(api.dg)
        api.push_and_create_pr(
            pr_title=self.commit_msg,
            pr_description=PR_DESCRIPTION,
            repo=api.dg,
            git_branch=default_dg_branch,
        )

    def handle_push(self, api: PackitAPI, default_dg_branch: str):
        self.write_package_config()
        self.commit_config(api.dg)
        api.dg.push(refspec=f"HEAD:{default_dg_branch}")

    def write_package_config(self):
        logger.info(f"Writing config to {self.config_path}")
        self.config_path.write_text(self.package_config_content)

    def commit_config(self, dist_git: DistGit):
        logger.info("About to add and commit the config.")
        dist_git.local_project.git_repo.index.add([CONFIG_FILE_NAME])
        dist_git.local_project.git_repo.index.commit(self.commit_msg)
