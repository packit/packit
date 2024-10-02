# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pprint
import re
import sys
from pathlib import Path

import black
import fedora_distro_aliases

ALIASES_SOURCE = Path("packit/config/aliases.py")

ALIASES_FALLBACK_PATTERN = re.compile(
    r"^(ALIASES.*?\s+=\s+){.*?}",
    re.MULTILINE | re.DOTALL,
)


def get_aliases():
    def format_name(distro):
        if distro.id_prefix == "FEDORA":
            return distro.long_name.lower().replace(" ", "-")
        return distro.name.lower()

    return {
        alias: [format_name(d) for d in distros]
        for alias, distros in fedora_distro_aliases.get_distro_aliases().items()
    }


def update_aliases_fallback():
    aliases = black.format_str(pprint.pformat(get_aliases()), mode=black.Mode())
    original_code = ALIASES_SOURCE.read_text()
    updated_code = re.sub(
        ALIASES_FALLBACK_PATTERN,
        rf"\g<1>{aliases[:-1]}",
        original_code,
    )
    if updated_code == original_code:
        return False
    ALIASES_SOURCE.write_text(updated_code)
    return True


def main():
    if not update_aliases_fallback():
        sys.exit(100)


if __name__ == "__main__":
    main()
