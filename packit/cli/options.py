# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Reusable Click option decorators for CLI commands.

This module provides common option decorators that can be shared across
multiple CLI commands to avoid duplication and ensure consistency.
"""

import click


def preserve_spec_option(f):
    """
    Add --preserve-spec option to a Click command.

    This option prevents spec file modifications during operations like
    SRPM creation or source preparation. When enabled, it implies
    --no-update-release.
    """
    return click.option(
        "--preserve-spec",
        is_flag=True,
        default=False,
        help=(
            "Do not update spec file during SRPM creation "
            "(implies --no-update-release). "
            "By default, spec file is updated."
        ),
    )(f)
