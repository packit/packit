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

# fedmsg topics
URM_NEW_RELEASE_TOPIC = "org.release-monitoring.prod.anitya.project.version.update"
# example:
# https://apps.fedoraproject.org/datagrepper/id?id=2019-a5034b55-339d-4fa5-a72b-db74579aeb5a
GH2FED_RELEASE_TOPIC = "org.fedoraproject.prod.github.release"

DEFAULT_BODHI_NOTE = "New upstream release: {version}"

PROD_DISTGIT_URL = "https://src.fedoraproject.org/"

DEFAULT_COPR_OWNER = "packit"

COPR2GITHUB_STATE = {
    "running": ("pending", "SRPM or RPM build is running"),
    "pending": ("pending", "build(-chroot) is waiting to be picked"),
    "starting": ("pending", "build was picked by worker but no VM initialized yet"),
    "importing": ("pending", "SRPM is being imported into dist-git"),
    "forked": ("pending", "build(-chroot) was forked"),
    "waiting": ("pending", "build(-chroot) is waiting for something else to finish"),
    "succeeded": ("success", "build succeeded"),
    "failed": ("failure", "build failed"),
    "canceled": ("error", "build was canceled"),
    "skipped": ("error", "if there was this package built already"),
    "unknown": ("error", "undefined"),
}
