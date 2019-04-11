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
import subprocess

from rebasehelper.specfile import SpecFile

from tests.spellbook import TARBALL_NAME, git_add_and_commit


def test_basic_local_update_without_patching(
    sourcegit_n_distgit,
    mock_patching,
    mock_remote_functionality_sourcegit,
    api_instance_source_git,
):
    """ propose-update for sourcegit test: mock remote API, use local upstream and dist-git """

    sourcegit, distgit = sourcegit_n_distgit

    api_instance_source_git.sync_release("master", "0.1.0", upstream_ref="0.1.0")

    assert (distgit / TARBALL_NAME).is_file()
    spec = SpecFile(str(distgit / "beer.spec"), None)
    assert spec.get_version() == "0.1.0"


def test_basic_local_update_patching(
    sourcegit_n_distgit, mock_remote_functionality_sourcegit, api_instance_source_git
):
    """ propose-update for sourcegit test: mock remote API, use local upstream and dist-git """

    sourcegit, distgit = sourcegit_n_distgit
    api_instance_source_git.sync_release("master", "0.1.0", upstream_ref="0.1.0")

    assert (distgit / TARBALL_NAME).is_file()
    spec = SpecFile(str(distgit / "beer.spec"), None)
    assert spec.get_version() == "0.1.0"

    spec_package_section = "\n".join(spec.spec_content.sections["%package"])
    assert "# PATCHES FROM SOURCE GIT" in spec_package_section
    assert "# sourcegit content" in spec_package_section
    assert "Patch0001: 0001" in spec_package_section

    spec_package_section_split = spec_package_section.split("# PATCHES FROM SOURCE GIT")
    assert "Source" in spec_package_section_split[0]
    assert "Source" not in spec_package_section_split[1]


def test_basic_local_update_patch_content(
    sourcegit_n_distgit, mock_remote_functionality_sourcegit, api_instance_source_git
):
    """ propose-update for sourcegit test: mock remote API, use local upstream and dist-git """

    sourcegit, distgit = sourcegit_n_distgit

    source_file = sourcegit / "big-source-file.txt"
    source_file.write_text("new changes")
    git_add_and_commit(directory=sourcegit, message="source change")

    api_instance_source_git.sync_release("master", "0.1.0", upstream_ref="0.1.0")

    spec = SpecFile(str(distgit / "beer.spec"), None)

    spec_package_section = "\n".join(spec.spec_content.sections["%package"])
    assert "Patch0001: 0001" in spec_package_section
    assert "Patch0002: 0002" in spec_package_section
    git_diff = subprocess.check_output(
        ["git", "diff", "HEAD~", "HEAD"], cwd=distgit
    ).decode()

    assert "-Version:        0.0.0\n+Version:        0.1.0" in git_diff
    assert "+# PATCHES FROM SOURCE GIT:" in git_diff
    assert (
        "-* Mon Feb 24 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.0.0-1\n"
        "-- No brewing, yet.\n"
        "+* Mon Feb 25 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.1.0-1\n"
        "+- Initial brewing" in git_diff
    )

    # direct diff in the synced file
    assert (
        "diff --git a/.packit.json b/.packit.json\n"
        "new file mode 100644\n"
        "index 0000000..efa8e00\n"
        "--- /dev/null\n"
        "+++ b/.packit.json" in git_diff
    )

    # diff of the synced file should not be in the patch
    assert (
        "+diff --git a/.packit.json b/.packit.json\n"
        "+new file mode 100644\n" not in git_diff
    )

    # diff of the source file (not synced) has to be in the patch
    assert (
        "patch\n"
        "@@ -0,0 +1,9 @@\n"
        "+diff --git a/big-source-file.txt b/big-source-file.txt\n" in git_diff
    )

    assert (
        "+--- a/big-source-file.txt\n"
        "++++ b/big-source-file.txt\n"
        "+@@ -1,2 +1 @@\n"
        "+-This is a testing file\n"
        "+-containing some text.\n"
        "++new changes\n" in git_diff
    )

    # diff of the source files (not synced) should not be directly in the git diff
    assert (
        "--- a/big-source-file.txt\n"
        "+++ b/big-source-file.txt\n"
        "@@ -1,2 +1 @@\n"
        "-This is a testing file\n"
        "-containing some text.\n"
        "+new changes\n" not in git_diff
    )
