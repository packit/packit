# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import xml.etree.ElementTree as ET

import pytest

from packit.utils import obs_helper

_NAME = "home:me:packit"
_TITLE = "Packit project"
_PERSON = "me"

head = f"""<project name="{_NAME}">
  <title>{_TITLE}</title>
  <description/>
  <person userid="{_PERSON}" role="maintainer"/>
"""
tail = """</repository>
</project>
"""


@pytest.mark.usefixtures("mock_get_aliases")
class TestTargetsToProject:
    @pytest.mark.parametrize(
        "targets,project_meta",
        [
            (
                ["fedora-rawhide-x86_64"],
                head
                + """
<repository name="fedora-rawhide-x86_64">
  <path project="Fedora:Rawhide" repository="standard"/>
  <arch>x86_64</arch>
"""
                + tail,
            ),
            (
                ["fedora-rawhide-x86_64", "fedora-rawhide-aarch64"],
                head
                + """
<repository name="fedora-rawhide-x86_64-aarch64">
  <path project="Fedora:Rawhide" repository="standard"/>
  <arch>x86_64</arch>
  <arch>aarch64</arch>
"""
                + tail,
            ),
            (
                [
                    "fedora-rawhide-x86_64",
                    "opensuse-leap-15.5-x86_64",
                    "fedora-rawhide-aarch64",
                    "opensuse-leap-15.5-ppc64le",
                    "opensuse-tumbleweed-x86_64",
                ],
                head
                + """
<repository name="fedora-rawhide-x86_64-aarch64">
  <path project="Fedora:Rawhide" repository="standard"/>
  <arch>x86_64</arch>
  <arch>aarch64</arch>
</repository>
<repository name="opensuse-leap-15.5-x86_64-ppc64le">
  <path project="openSUSE:Leap:15.5" repository="standard"/>
  <arch>x86_64</arch>
  <arch>ppc64le</arch>
</repository>
<repository name="opensuse-tumbleweed-x86_64">
  <path project="openSUSE:Factory" repository="snapshot"/>
  <arch>x86_64</arch>
"""
                + tail,
            ),
        ],
    )
    def test_targets_to_project(
        self,
        targets: list[str],
        project_meta: str,
        mock_get_aliases,
    ) -> None:
        assert ET.canonicalize(project_meta, strip_text=True) == ET.canonicalize(
            ET.tostring(
                obs_helper.targets_to_project_meta(
                    targets,
                    owner=_PERSON,
                    project_name=f"home:{_PERSON}:packit",
                ),
            ),
            strip_text=True,
        )


changelog = (
    "* Thu Aug 01 2024 Packit Team <hello@packit.dev> - 0.100.1-1\n"
    + "- New upstream release 0.100.1\n"
    + "* Mon Jul 29 2024 Packit Team <hello@packit.dev> - 0.100.0-1\n"
    + "- New upstream release 0.100.0\n"
    + "* Fri May  2 2003 Elliot Lee <sopwith@redhat.com>\n"
    + "- Add emacs-21.3-ppc64.patch\n"
    + "* Fri Jun 23 2006 Jesse Keating <jkeating@redhat.com> 0.6-4\n"
    + "- And fix the link syntax.\n"
    + "* Fri Jun 23 2006 Jesse Keating <jkeating@redhat.com>\n"
    + "- 0.6-4\n"
    + "- And fix the link syntax."
)

obs_changelog = (
    "--------------------------------------------------------------------\n"
    + "Thu Aug 01 12:00:00 UTC 2024 - Packit Team <hello@packit.dev>\n\n"
    + "- 0.100.1-1\n"
    + "  - New upstream release 0.100.1\n\n"
    + "--------------------------------------------------------------------\n"
    + "Mon Jul 29 12:00:00 UTC 2024 - Packit Team <hello@packit.dev>\n\n"
    + "- 0.100.0-1\n"
    + "  - New upstream release 0.100.0\n\n"
    + "--------------------------------------------------------------------\n"
    + "Fri May 2 12:00:00 UTC 2003 - Elliot Lee <sopwith@redhat.com>\n\n"
    + "  - Add emacs-21.3-ppc64.patch\n\n"
    + "--------------------------------------------------------------------\n"
    + "Fri Jun 23 12:00:00 UTC 2006 - Jesse Keating <jkeating@redhat.com>\n\n"
    + "- 0.6-4\n"
    + "  - And fix the link syntax.\n\n"
    + "--------------------------------------------------------------------\n"
    + "Fri Jun 23 12:00:00 UTC 2006 - Jesse Keating <jkeating@redhat.com>\n\n"
    + "- 0.6-4\n"
    + "  - And fix the link syntax."
)


def test_format_changelog_to_obs_format():
    assert obs_changelog == obs_helper.format_changelog(changelog)
