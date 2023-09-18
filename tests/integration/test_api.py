# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""    custom_path = "sooooorc.rpm"
Functional tests for srpm comand
"""
from pathlib import Path


def test_srpm(cwd_upstream_or_distgit, api_instance):
    u, d, api = api_instance
    api.create_srpm()
    assert next(Path.cwd().glob("*.src.rpm")).exists()


def test_srpm_custom_path(cwd_upstream_or_distgit, api_instance):
    u, d, api = api_instance
    custom_path = "sooooorc.rpm"
    api.create_srpm(output_file=custom_path)
    assert Path.cwd().joinpath(custom_path).is_file()
