import xml.etree.ElementTree as ET

import pytest

from packit.utils.obs_helper import OBSHelper

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
                OBSHelper.targets_to_project_meta(
                    targets,
                    owner=_PERSON,
                    project_name=f"home:{_PERSON}:packit",
                ),
            ),
            strip_text=True,
        )
