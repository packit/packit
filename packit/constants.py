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

DG_PR_COMMENT_KEY_SG_PR = "Source-git pull request ID"
DG_PR_COMMENT_KEY_SG_COMMIT = "Source-git commit"
CONFIG_FILE_NAMES = [
    ".packit.yaml",
    ".packit.yml",
    ".packit.json",
    "packit.yaml",
    "packit.yml",
    "packit.json",
]

DATETIME_FORMAT = "%Y%m%d%H%M%S%f"

# we create .tar.gz archives
DEFAULT_ARCHIVE_EXT = ".tar.gz"

DEFAULT_BODHI_NOTE = "New upstream release: {version}"

PROD_DISTGIT_HOSTNAME = "src.fedoraproject.org"
PROD_DISTGIT_URL = f"https://{PROD_DISTGIT_HOSTNAME}/"
ALTERNATIVE_PROD_DG_HOSTNAME = "pkgs.fedoraproject.org"
DIST_GIT_HOSTNAME_CANDIDATES = (
    PROD_DISTGIT_HOSTNAME,
    ALTERNATIVE_PROD_DG_HOSTNAME,
    "pkgs.stg.fedoraproject.org",
    "src.stg.fedoraproject.org",
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

specfile_path: {downstream_package_name}.spec

# add or remove files that should be synced
synced_files:
    - {downstream_package_name}.spec
    - .packit.yaml

# name in upstream package repository/registry (e.g. in PyPI)
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

SPEC_PACKAGE_SECTION = "%package"
