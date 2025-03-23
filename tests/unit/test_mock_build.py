# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

def test_build_in_mock_default_resultdir():
    result = run_packit_command(["build", "in-mock"])
    assert os.path.exists("./some_expected_file")
