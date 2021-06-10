# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import flexmock
import pytest
import textwrap
import shutil

from pathlib import Path

from packit.specfile import Specfile
from tests.spellbook import SPECFILE


@pytest.fixture(scope="function")
def specfile(tmp_path):
    specfile_path = tmp_path / "beer.spec"
    shutil.copyfile(SPECFILE, specfile_path)
    return specfile_path


def test_write_spec_content(specfile):
    data = "new line 1\n"
    spec = Specfile(specfile)
    spec.spec_content.replace_section("%description", [data])
    spec.write_spec_content()

    assert "new line 1" in specfile.read_text()


@pytest.mark.parametrize("patch_id_digits", [{}, {"patch_id_digits": 0}])
def test_add_patch(specfile, patch_id_digits):
    """Check adding patch lines to the spec-file.

    Change the number of digits, too, to see that it's considered.
    """
    assert "Patch" not in specfile.read_text()

    spec = Specfile(specfile, sources_dir=specfile.parent)
    patch_meta = flexmock(
        name="0001-a-clever.patch",
        specfile_comment="This needs to be added because of\nBug 111",
        patch_id=None,
    )
    Path(specfile.parent, "0001-a-clever.patch").touch()
    spec.add_patch(patch_meta, **patch_id_digits)

    patch_meta = flexmock(
        name="0002-an-even-smarter.patch",
        specfile_comment="This needs to be added because of\nBug 22",
        patch_id=None,
    )
    Path(specfile.parent, "0002-an-even-smarter.patch").touch()
    spec.add_patch(patch_meta, **patch_id_digits)

    patch_lines = textwrap.dedent(
        f"""\
        # This needs to be added because of
        # Bug 111
        Patch{1:0{patch_id_digits.get('patch_id_digits', 4)}d}: 0001-a-clever.patch

        # This needs to be added because of
        # Bug 22
        Patch{2:0{patch_id_digits.get('patch_id_digits', 4)}d}: 0002-an-even-smarter.patch
        """
    )
    assert patch_lines in specfile.read_text()


simple_patch = """\
# A bright yellow patch
Patch1: yellow.patch
"""

patch_with_url = """\
# A bright yellow patch
Patch0001  :  https://inter.netz/yellow.patch\n
"""

multiple_patches = """\
# An interesting purple
Patch0200: purple.patch

# Orange is a fruit
# And orange is a colour
Patch0301: orange.patch
"""

hanging_comments = """\
# This comment doesn't belong to any patch

Patch: surprise.patch
"""

no_space = """\
# An interesting purple
Patch0200: purple.patch
# Orange is a fruit
Patch0301: orange.patch
"""


@pytest.mark.parametrize(
    "lines,files,expectation",
    [
        (simple_patch, ["yellow.patch"], {"yellow.patch": ["A bright yellow patch"]}),
        (patch_with_url, ["yellow.patch"], {"yellow.patch": ["A bright yellow patch"]}),
        (
            multiple_patches,
            ["purple.patch", "orange.patch"],
            {
                "purple.patch": ["An interesting purple"],
                "orange.patch": ["Orange is a fruit", "And orange is a colour"],
            },
        ),
        (hanging_comments, ["surprise.patch"], {"surprise.patch": []}),
        (
            no_space,
            ["purple.patch", "orange.patch"],
            {
                "purple.patch": ["An interesting purple"],
                "orange.patch": ["Orange is a fruit"],
            },
        ),
    ],
    ids=[
        "simple-patch",
        "patch-with-url",
        "multiple-patches",
        "hanging-comments",
        "no-space",
    ],
)
def test_read_patch_comments(specfile, lines, files, expectation):
    content = specfile.read_text()
    content = content.replace("### patches ###\n", lines)
    specfile.write_text(content)
    for patch_file in files:
        Path(specfile.parent, patch_file).touch()
    spec = Specfile(specfile, sources_dir=specfile.parent)
    comments = spec.read_patch_comments()
    assert comments == expectation
