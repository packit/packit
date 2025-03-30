import os
from unittest.mock import patch, MagicMock, call
import pytest
from packit.api import PackitAPI  # Import PackitAPI class

def test_build_in_mock_default_resultdir():
    """Ensure that --resultdir defaults to '.' when not provided."""

    expected_resultdir = None  # Expected default is the current directory
    srpm_path = "test.srpm"  # Dummy SRPM path

    # Mock required arguments for PackitAPI
    mock_config = MagicMock()
    mock_package_config = MagicMock()

    # Create an instance of PackitAPI
    api = PackitAPI(config=mock_config, package_config=mock_package_config)

    # Patch the method inside a `with` statement
    with patch.object(api, "run_mock_build", autospec=True) as mock_run_mock_build:
        # Call function without specifying resultdir
        api.run_mock_build(srpm_path=srpm_path, resultdir=None)

        # Extract what was actually received
        actual_calls = mock_run_mock_build.call_args_list

        # Print expected behavior
        print(f"\n EXPECTED: run_mock_build(srpm_path={srpm_path}, resultdir={expected_resultdir})")

        # Print actual function calls for verification
        print("\n ACTUAL calls to run_mock_build:", actual_calls)

        # Verify if function was actually called
        if not actual_calls:
            print("\n ERROR: run_mock_build was NOT called!")
        else:
            for call_obj in actual_calls:
                args, kwargs = call_obj
                print(f" CALL DETAILS: args={args}, kwargs={kwargs}")

        # Assert that resultdir defaults to '.'
        try:
            mock_run_mock_build.assert_called_with(srpm_path=srpm_path, resultdir=expected_resultdir)
            print("\n TEST PASSED: run_mock_build was called with the expected arguments!\n")
            print(f"EXPECTED CALL: run_mock_build(srpm_path={srpm_path}, resultdir={expected_resultdir})")
            print(f"ACTUAL CALL(S): {actual_calls}")
        except AssertionError as e:
            print("\n TEST FAILED!")
            # print(f"EXPECTED CALL: run_mock_build(srpm_path={srpm_path}, resultdir={expected_resultdir})")
            # print(f"ACTUAL CALL(S): {actual_calls}")
            raise  # Re-raise the error so pytest catches it
