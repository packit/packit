# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

DG_PR_COMMENT_KEY_SG_PR = "Source-git pull request ID"
DG_PR_COMMENT_KEY_SG_COMMIT = "Source-git commit"

# we store downstream content in source-git in this subdir
DISTRO_DIR = ".distro"
SRC_GIT_CONFIG = "source-git.yaml"
CONFIG_FILE_NAMES = [
    f"{DISTRO_DIR}/{SRC_GIT_CONFIG}",
    ".packit.yaml",
    ".packit.yml",
    ".packit.json",
    "packit.yaml",
    "packit.yml",
    "packit.json",
]

# local branch name when checking out a PR before we merge it with the target branch
LP_TEMP_PR_CHECKOUT_NAME = "pr-changes"

DATETIME_FORMAT = "%Y%m%d%H%M%S%f"

# we create .tar.gz archives
DEFAULT_ARCHIVE_EXT = ".tar.gz"

DEFAULT_BODHI_NOTE = "New upstream release: {version}"

FEDORA_DOMAIN = "fedoraproject.org"

PROD_DISTGIT_HOSTNAME = f"src.{FEDORA_DOMAIN}"
PROD_DISTGIT_URL = f"https://{PROD_DISTGIT_HOSTNAME}/"

DISTGIT_NAMESPACE = "rpms"

ALTERNATIVE_PROD_DG_HOSTNAME = f"pkgs.{FEDORA_DOMAIN}"
STG_DISTGIT_HOSTNAME = f"src.stg.{FEDORA_DOMAIN}"
ALTERNATIVE_STG_DG_HOSTNAME = f"pkgs.stg.{FEDORA_DOMAIN}"

DIST_GIT_HOSTNAME_CANDIDATES = (
    PROD_DISTGIT_HOSTNAME,
    ALTERNATIVE_PROD_DG_HOSTNAME,
    STG_DISTGIT_HOSTNAME,
    ALTERNATIVE_STG_DG_HOSTNAME,
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

# add or remove files that should be synced
files_to_sync:
    - {specfile_path}
    - .packit.yaml

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
    "_packitpatch %{1} %{2} %{-p:-p%{-p*}} %{-q:-s} --fuzz=%{_default_patch_fuzz} "
    "%{_default_patch_flags}",
    # override patch program with _packitpatch
    "-D",
    "__patch _packitpatch %{1} %{2} %{-p:-p%{-p*}} %{-q:-s} "
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
packit -d prepare-sources --result-dir "$resultdir" {options}

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
}
