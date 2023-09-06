# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.utils.changelog_helper import ChangelogHelper


@pytest.mark.parametrize(
    "original, sanitized",
    [
        ("- 100% of tests now pass", "- 100% of tests now pass"),
        ("- removed all %global macros", "- removed all %%global macros"),
        ("- cleaned up %install section", "- cleaned up %%install section"),
        (
            "- got rid of all shell (%(...)) and expression (%[...]) expansions",
            "- got rid of all shell (%%(...)) and expression (%%[...]) expansions",
        ),
        ("- first item\n* second item", "- first item\n * second item"),
        ("* first item\n* second item", " * first item\n * second item"),
    ],
)
def test_sanitize_entry(original, sanitized):
    assert ChangelogHelper.sanitize_entry(original) == sanitized
