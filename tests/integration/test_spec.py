# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
import textwrap
import shutil
import rpm

from flexmock import flexmock
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


@pytest.mark.parametrize("patch_id_digits", [4, 1, 0])
def test_add_patch(specfile, patch_id_digits):
    """Check adding patch lines to the spec-file.

    Change the number of digits, too, to see that it's considered.
    """
    if rpm.__version__ < "4.16" and patch_id_digits == 0:
        pytest.xfail(
            "Versions before RPM 4.16 have incorrect patch indexing "
            "when an index is not explicitly defined. "
            "'patch_id_digits: 0' is not supported with these versions."
        )

    assert "Patch" not in specfile.read_text()

    spec = Specfile(specfile, sources_dir=specfile.parent)
    patch_meta = flexmock(
        name="0001-a-clever.patch",
        specfile_comment="This needs to be added because of\nBug 111",
        patch_id=None,
    )
    Path(specfile.parent, "0001-a-clever.patch").touch()
    spec.add_patch(patch_meta, patch_id_digits=patch_id_digits)

    patch_meta = flexmock(
        name="0022-an-even-smarter.patch",
        specfile_comment="This needs to be added because of\nBug 22",
        patch_id=22,
    )
    Path(specfile.parent, "0022-an-even-smarter.patch").touch()
    spec.add_patch(patch_meta, patch_id_digits=patch_id_digits)

    patch_tags = (
        [f"Patch{1:0{patch_id_digits}d}", f"Patch{22:0{patch_id_digits}d}"]
        if patch_id_digits > 0
        else ["Patch", "Patch"]
    )
    patch_lines = textwrap.dedent(
        f"""\
        # This needs to be added because of
        # Bug 111
        {patch_tags[0]}: 0001-a-clever.patch

        # This needs to be added because of
        # Bug 22
        {patch_tags[1]}: 0022-an-even-smarter.patch
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
    """Check reading comment lines that belong to patches"""
    content = specfile.read_text()
    content = content.replace("### patches ###\n", lines)
    specfile.write_text(content)
    for patch_file in files:
        Path(specfile.parent, patch_file).touch()
    spec = Specfile(specfile, sources_dir=specfile.parent)
    comments = spec.read_patch_comments()
    assert comments == expectation


@pytest.mark.parametrize(
    "lines,digits",
    [
        ("Patch0001 : some.patch\n", 4),
        ("Patch003000 : some.patch\n", 6),
        ("Patch: some.patch\n", 0),
        ("Patch21: some.patch\n", 1),
        ("Patch9: some.patch\n", 1),
    ],
)
def test_patch_id_digits(specfile, lines, digits):
    """Check detecting the number of digits used for patch IDs (indices)"""
    content = specfile.read_text()
    content = content.replace("### patches ###\n", lines)
    specfile.write_text(content)
    spec = Specfile(specfile, sources_dir=specfile.parent)
    assert spec.patch_id_digits == digits


def test_remove_patches(specfile):
    """Check patches being removed from a specfile"""
    no_patches = specfile.read_text().replace("\n### patches ###\n", "")
    patches = specfile.read_text().replace(
        "### patches ###\n",
        """\
# Some comment line to be removed
Patch1: yellow.patch

Patch2: blue.patch
# One
# Or more lines
Patch : dark.patch
""",
    )
    specfile.write_text(patches)
    spec = Specfile(specfile, sources_dir=specfile.parent)
    spec.remove_patches()
    assert specfile.read_text() == no_patches


def test_remove_patches_no_blanklines(specfile):
    no_blanks = specfile.read_text().replace("\n\n", "\n")
    no_patches = no_blanks.replace("\n### patches ###\n", "\n")
    patches = no_blanks.replace(
        "### patches ###\n",
        """\
# Some comment line to be removed
Patch1: yellow.patch
Patch2: blue.patch
# One
# Or more lines
Patch : dark.patch
""",
    )
    specfile.write_text(patches)
    spec = Specfile(specfile, sources_dir=specfile.parent)
    spec.remove_patches()
    assert specfile.read_text() == no_patches
