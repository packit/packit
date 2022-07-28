# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
import shutil

from pathlib import Path
from specfile import Specfile

from tests.spellbook import SPECFILE


@pytest.fixture(scope="function")
def specfile(tmp_path):
    specfile_path = tmp_path / "beer.spec"
    shutil.copyfile(SPECFILE, specfile_path)
    return specfile_path


def test_write_spec_content(specfile):
    data = "new line 1\n"
    spec = Specfile(specfile, autosave=True)
    with spec.sections() as sections:
        sections.description = [data]

    assert "new line 1" in specfile.read_text()


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
    spec = Specfile(specfile, sourcedir=specfile.parent, autosave=True)
    with spec.patches() as patches:
        comments = {p.filename: [c.text for c in p.comments] for p in patches}
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
    spec = Specfile(specfile, sourcedir=specfile.parent, autosave=True)
    with spec.patches() as patches:
        assert patches[0].number_digits == digits


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
    spec = Specfile(specfile, sourcedir=specfile.parent, autosave=True)
    with spec.patches() as patches:
        patches.clear()
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
    spec = Specfile(specfile, sourcedir=specfile.parent, autosave=True)
    with spec.patches() as patches:
        patches.clear()
    assert specfile.read_text() == no_patches
