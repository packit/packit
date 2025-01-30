# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import itertools

from packit.dist_git_instance import DistGitInstance

DG_PR_COMMENT_KEY_SG_PR = "Source-git pull request ID"
DG_PR_COMMENT_KEY_SG_COMMIT = "Source-git commit"

# we store downstream content in source-git in this subdir
DISTRO_DIR = ".distro"
SRC_GIT_CONFIG = "source-git.yaml"
CONFIG_FILE_NAMES = {
    ".packit.yaml",
    ".packit.yml",
    "packit.yaml",
    "packit.yml",
}

# local branch name when checking out a PR before we merge it with the target branch
LP_TEMP_PR_CHECKOUT_NAME = "pr-changes"

DATETIME_FORMAT = "%Y%m%d%H%M%S%f"

# we create .tar.gz archives
DEFAULT_ARCHIVE_EXT = ".tar.gz"

DEFAULT_BODHI_NOTE = "New upstream release: {version}"
EXISTING_BODHI_UPDATE_REGEX = r".*Update for \S+ already exists.*"

FEDORA_DOMAIN = "fedoraproject.org"

DISTGIT_INSTANCES = {
    "fedpkg": DistGitInstance(
        hostname=f"src.{FEDORA_DOMAIN}",
        alternative_hostname=f"pkgs.{FEDORA_DOMAIN}",
        namespace="rpms",
    ),
    "fedpkg-stage": DistGitInstance(
        hostname=f"src.stg.{FEDORA_DOMAIN}",
        alternative_hostname=f"pkgs.stg.{FEDORA_DOMAIN}",
        namespace="rpms",
    ),
    "centpkg": DistGitInstance(
        hostname="gitlab.com",
        alternative_hostname=None,
        namespace="redhat/centos-stream/rpms",
    ),
    "centpkg-sig": DistGitInstance(
        hostname="gitlab.com",
        alternative_hostname=None,
        namespace="CentOS/{sig}/rpms",
    ),
}

DISTGIT_HOSTNAME_CANDIDATES = set(
    filter(
        lambda hostname: hostname is not None,
        itertools.chain.from_iterable(
            (distgit.hostname, distgit.alternative_hostname)
            for distgit in DISTGIT_INSTANCES.values()
        ),
    ),
)

COPR2GITHUB_STATE = {
    "running": ("pending", "The RPM build was triggered."),
    "pending": ("pending", "The RPM build has started."),
    "starting": ("pending", "The RPM build has started."),
    "importing": ("pending", "The RPM build has started."),
    "forked": ("pending", "The RPM build has started."),
    "waiting": ("pending", "The RPM build is in progress."),
    "succeeded": ("success", "RPMs were built successfully."),
    "failed": ("failure", "RPMs failed to be built."),
    "canceled": ("error", "The RPM build was canceled."),
    "skipped": ("error", "The build was already done."),
    "unknown": ("error", "Something went wrong."),
}

PACKIT_CONFIG_TEMPLATE = """# See the documentation for more information:
# https://packit.dev/docs/configuration/

specfile_path: {specfile_path}

# name in upstream package repository or registry (e.g. in PyPI)
upstream_package_name: {upstream_package_name}
# downstream (Fedora) RPM package name
downstream_package_name: {downstream_package_name}
"""

SANDCASTLE_WORK_DIR = "/sandcastle"
SANDCASTLE_IMAGE = "docker.io/usercont/sandcastle"
SANDCASTLE_DEFAULT_PROJECT = "myproject"
SANDCASTLE_PVC = "SANDCASTLE_PVC"

SYNCING_NOTE = (
    "This repository is maintained by packit.\nhttps://packit.dev/\n"
    "The file was generated using packit {packit_version}.\n"
)

PATCH_META_TRAILER_TOKENS = {
    "Patch-name",
    "Patch-id",
    "Patch-status",
    "Patch-present-in-specfile",
    "Ignore-patch",
    "No-prefix",
}

# shell code wrapped in lua as a python constant, what could go wrong?
# for real now: this horror is being used when creating source-git repos from upstream
# these macros override RPM default macros for setup and patching so that
# `rpmbuild -bp` leaves a git repo after invoking %prep
RPM_MACROS_FOR_PREP = [
    # we want both 'git init': here and in _packitpatch
    # if there are no patches, _packitpatch never gets invoked and
    # this will be invoked b/c of %autosetup
    "-D",
    "__scm_setup_patch(q) "
    "%{__git} init && "
    "%{__git} add -f . && "
    '%{__git} commit -q --allow-empty -a -m "%{NAME}-%{VERSION} base"',
    # %{1} = absolute path to the patch
    # %{2} = patch ID
    "-D",
    "__scm_apply_patch(qp:m:) "
    "%_packitpatch %{1} %{2} %{-p:-p%{-p*}} %{-q:-s} --fuzz=%{_default_patch_fuzz} "
    "%{_default_patch_flags}",
    # override patch program with _packitpatch
    "-D",
    "__patch %_packitpatch %{1} %{2} %{-p:-p%{-p*}} %{-q:-s} "
    "--fuzz=%{_default_patch_fuzz} %{_default_patch_flags}",
    "-D",
    "__scm_setup_git(q) "
    "%{__git} init %{-q} && "
    "%{__git} add -f . && "
    '%{__git} commit -q --allow-empty -a -m "%{NAME}-%{VERSION} base"',
    # commit_msg contains commit message of the last commit
    "-D",
    "__scm_apply_git_am(qp:m:) "
    "%{__git} am %{-q} %{-p:-p%{-p*}} && "
    "patch_name=`basename %{1}` && "
    "commit_msg=`%{__git} log --format=%B -n1` && "
    r'metadata_commit_msg=`printf "Patch-name: $patch_name"` && '
    '%{__git} commit --amend -m "$commit_msg" -m "$metadata_commit_msg"',
    # do the same of %autosetup -Sgit
    # that is, apply packit patch metadata to the patch commit
    # so packit can create the matching patch file
    "-D",
    "__scm_apply_git(qp:m:) "
    "%{__git} apply --index %{-p:-p%{-p*}} - && "
    "patch_name=`basename %{1}` && "
    r'metadata_commit_msg=`printf "Patch-name: $patch_name\\n"` && '
    '%{__git} commit %{-q} -m %{-m*} -m "${metadata_commit_msg}" --author "%{__scm_author}"',
]

COPR_SOURCE_SCRIPT = """
#!/bin/sh

git config --global user.email "hello@packit.dev"
git config --global user.name "Packit"
resultdir=$PWD
packit -d prepare-sources{package} --result-dir "$resultdir" {options}

"""

# Git-trailer tokens to mark the commit origin
FROM_DIST_GIT_TOKEN = "From-dist-git-commit"
FROM_SOURCE_GIT_TOKEN = "From-source-git-commit"

REPO_NOT_PRISTINE_HINT = (
    "Use 'git reset --hard HEAD' to reset changed files and "
    "'git clean -xdff' to delete untracked files and directories."
)

KOJI_BASEURL = "https://koji.fedoraproject.org/kojihub"

# key name -> default
CHROOT_SPECIFIC_COPR_CONFIGURATION = {
    "additional_packages": [],
    "additional_repos": [],
    # modules default to string because Copr stores it as string in the DB
    "additional_modules": "",
    "with_opts": [],
    "without_opts": [],
}

PACKAGE_LONG_OPTION = "--package"
PACKAGE_SHORT_OPTION = "-p"
PACKAGE_OPTION_HELP = (
    "Package to {action}, if more than one available, "
    "like in a monorepo configuration. "
    "Use it multiple times to select multiple packages."
    "Defaults to all the packages listed inside the config."
)

SYNC_RELEASE_DEFAULT_COMMIT_DESCRIPTION = (
    "{resolved_bugs}{upstream_tag}\n"
    "{upstream_commit_info}\n"
    "\n"
    "Commit authored by Packit automation (https://packit.dev/)\n"
)

SYNC_RELEASE_PR_DESCRIPTION = (
    "{upstream_tag_info}\n"
    "{upstream_commit_info}\n"
    "{release_monitoring_info}"
    "{resolved_bugzillas_info}"
)

SYNC_RELEASE_PR_GITLAB_CLONE_INSTRUCTIONS = (
    "If you need to do any change in this pull request, follow "
    "the instructions under `Code -> Check out branch` in the right sidebar."
)

SYNC_RELEASE_PR_PAGURE_CLONE_INSTRUCTIONS = (
    "If you need to do any change in this pull request, you can clone Packit's fork "
    "and push directly to the source branch of this PR (provided you have commit access "
    "to this repository):\n"
    "```\n"
    "git clone ssh://$YOUR_USER@pkgs.fedoraproject.org/forks/{user}/rpms/{package}.git\n"
    "cd {package}\n"
    "git checkout {branch}\n"
    "git push origin {branch}\n"
    "```\n"
    "\n---\n\n"
    "Alternatively, if you already have the package repository cloned, "
    "you can just fetch the Packit's fork:\n"
    "```\n"
    "cd {package}\n"
    "git remote add packit ssh://$YOUR_USER@pkgs.fedoraproject.org/forks/{user}/rpms/{package}.git\n"
    "git fetch packit refs/heads/{branch}\n"
    "git checkout {branch}\n"
    "git push packit {branch}\n"
    "```"
)

SYNC_RELEASE_PR_KOJI_NOTE = (
    "If you have the `koji_build` job configured as well, make sure to configure "
    "the `allowed_pr_authors` and/or `allowed_committers` (see [the docs]"
    "(https://packit.dev/docs/configuration/downstream/koji_build#optional-parameters)) "
    "since by default, Packit reacts only to its own PRs."
)

SYNC_RELEASE_PR_CHECKLIST = (
    "Before pushing builds/updates, please remember to check the new "
    "version against the "
    "[packaging guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/).\n\n"
    "For example, please:\n\n"
    "- check that the new sources only contain permissible content\n"
    "- check that the license of the new version has not changed\n"
    "- check for any API/ABI and other changes that may break dependent packages\n"
    "- check the autogenerated changelog"
)

COMMIT_ACTION_DIVIDER = "---%<--- snip ---%<--- here ---%<---\n"
RELEASE_MONITORING_PROJECT_URL = "https://release-monitoring.org/project/{project_id}"
BUGZILLA_URL = "https://bugzilla.redhat.com/show_bug.cgi?id={bug_id}"
BUGZILLA_HOSTNAME = "bugzilla.redhat.com"
ANITYA_MONITORING_CHECK_URL = (
    "https://src.fedoraproject.org/_dg/anitya/rpms/{package_name}"
)
RELEASE_MONITORING_PACKAGE_CHECK_URL = "https://release-monitoring.org//api/v2/packages/?name={package_name}&distribution=Fedora"
DOWNSTREAM_PACKAGE_CHECK_URL = "https://src.fedoraproject.org/rpms/{package_name}"

# connection timeout and read timeout in seconds
# with connection timeout, the actual value will usually be a multiple of what is configured,
# depending on the number of IP addresses for the target domain
HTTP_REQUEST_TIMEOUT = (10, 30)

FAST_FORWARD_MERGE_INTO_KEY = "fast_forward_merge_into"
