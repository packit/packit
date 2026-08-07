#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""Generate a JSON Schema for the Packit package configuration.

This script uses ``marshmallow-jsonschema`` to introspect the
``PackageConfigSchema`` and output a JSON Schema file suitable for
submission to the `Schema Store <https://www.schemastore.org/>`_.

Usage::

    python scripts/generate_package_schema.py
    python scripts/generate_package_schema.py --output packit.schema.json

Requirements:
    marshmallow-jsonschema (install with ``pip install marshmallow-jsonschema``)
"""

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate JSON Schema for Packit package config",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("packit.schema.json"),
        help="Path to write the JSON Schema file (default: packit.schema.json)",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level (default: 2)",
    )
    args = parser.parse_args()

    try:
        from packit.schema import PackageConfigSchema
    except ImportError as e:
        print(
            f"Error: Could not import PackageConfigSchema from packit.schema.\n"
            f"Make sure packit is installed or PYTHONPATH is set correctly.\n"
            f"Details: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Generating JSON Schema from PackageConfigSchema...")
    try:
        schema = PackageConfigSchema.json_schema()
    except Exception as e:
        print(
            f"Error: Failed to generate JSON Schema.\n"
            f"Details: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=args.indent, ensure_ascii=False)
        f.write("\n")

    print(f"JSON Schema written to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
