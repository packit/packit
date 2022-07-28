# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import pytest
import rpm

from specfile import Specfile

spec = """
Name: bring-me-to-the-life
Version: 1.0
Release: 1
Source0: foo.bar
License: GPLv3+
Summary: evanescence
%description
-
%changelog
"""


@pytest.mark.parametrize(
    "spec_content, has_autochangelog",
    [
        pytest.param(
            spec
            + """
%autochangelog
""",
            True,
        ),
        pytest.param(
            spec
            + """
* Mon Mar 04 2019 Foo Bor <foo-bor@example.com> - 1.0-1
- Initial package.
""",
            False,
        ),
        pytest.param(
            spec
            + """
 # %autochangelog
""",
            False,
        ),
    ],
)
@pytest.mark.skipif(
    rpm.__version__ < "4.16", reason="%autochangelog requires rpm 4.16 or higher"
)
def test_set_spec_has_autochangelog(spec_content, has_autochangelog, tmp_path):
    spec_path = tmp_path / "life.spec"
    spec_path.write_text(spec_content)
    specfile = Specfile(spec_path, sourcedir=tmp_path, autosave=True)

    assert specfile.has_autochangelog == has_autochangelog
