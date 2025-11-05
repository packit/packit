# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from packit.utils.changelog_helper import ChangelogHelper


@pytest.mark.parametrize(
    "original, sanitized",
    [
        # No sanitization needed
        ("- 100% of tests now pass", "- 100% of tests now pass"),
        # RPM macro references that need escaping
        ("- removed all %global macros", "- removed all %%global macros"),
        ("- cleaned up %install section", "- cleaned up %%install section"),
        ("- updated %{version} tag", "- updated %%{version} tag"),
        (
            "- Use %{_bindir}/%{name} for %install",
            "- Use %%{_bindir}/%%{name} for %%install",
        ),
        (
            "- nested %{?version:.%{name}} macro",
            "- nested %%{?version:.%%{name}} macro",
        ),
        # Shell and expression expansions
        (
            "- got rid of all shell (%(...)) and expression (%[...]) expansions",
            "- got rid of all shell (%%(...)) and expression (%%[...]) expansions",
        ),
        # Already escaped - should not double-escape
        ("- already escaped %%global", "- already escaped %%global"),
        # Odd number of percent signs
        ("- weird %%%global combination", "- weird %%%%global combination"),
        # Asterisks at line start
        ("- first item\n* second item", "- first item\n * second item"),
        ("* first item\n* second item", " * first item\n * second item"),
    ],
)
def test_sanitize_entry(original, sanitized):
    assert ChangelogHelper.sanitize_entry(original) == sanitized
