# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Tests for Upstream class
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from flexmock import flexmock

from ogr import GithubService
from packit.local_project import LocalProject
from packit.upstream import Upstream
from packit.utils import cwd

try:
    from rebasehelper.plugins.plugin_manager import plugin_manager
except ImportError:
    from rebasehelper.versioneer import versioneers_runner

from packit.config import Config, get_local_package_config
from packit.exceptions import PackitException
from tests.testsuite_basic.spellbook import (
    does_bumpspec_know_new,
    build_srpm,
    get_test_config,
    initiate_git_repo,
    EMPTY_CHANGELOG,
)


def test_get_spec_version(upstream_instance):
    u, ups = upstream_instance
    assert ups.get_specfile_version() == "0.1.0"


def test_get_current_version(upstream_instance):
    u, ups = upstream_instance

    assert ups.get_current_version() == "0.1.0"


@pytest.mark.parametrize(
    "m_v,exp",
    (
        ("1.1000.1000000", "1.1000.1000000"),
        (None, "0.1.0"),
        ("0.0.3", "0.1.0"),
        ("176", "176"),
    ),
)
def test_get_version(upstream_instance, m_v, exp):
    u, ups = upstream_instance
    try:
        flexmock(plugin_manager.versioneers, run=lambda **kw: m_v)
    except NameError:
        flexmock(versioneers_runner, run=lambda **kw: m_v)

    assert ups.get_version() == exp

    u.joinpath("README").write_text("\nEven better now!\n")
    subprocess.check_call(["git", "add", "."], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "More awesome changes"], cwd=u)

    # 0.1.0.1.ge98cee1
    assert re.match(r"0\.1\.0\.1\.\w{8}", ups.get_current_version())


@pytest.mark.skipif(
    not does_bumpspec_know_new(),
    reason="Current version of rpmdev-bumpspec doesn't understand --new option.",
)
def test_bumpspec(upstream_instance):
    u, ups = upstream_instance

    new_ver = "1.2.3"
    ups.bump_spec(version=new_ver, changelog_entry="asdqwe")

    assert ups.get_specfile_version() == new_ver


def test_set_spec_ver(upstream_instance):
    u, ups = upstream_instance

    new_ver = "1.2.3"
    ups.set_spec_version(version=new_ver, changelog_entry="- asdqwe")

    assert ups.get_specfile_version() == new_ver
    assert "- asdqwe" in u.joinpath("beer.spec").read_text()


def test_set_spec_ver_empty_changelog(tmpdir):
    t = Path(str(tmpdir))

    u_remote_path = t / "upstream_remote"
    u_remote_path.mkdir(parents=True, exist_ok=True)

    subprocess.check_call(["git", "init", "--bare", "."], cwd=u_remote_path)

    u = t / "upstream_git"
    shutil.copytree(EMPTY_CHANGELOG, u)
    initiate_git_repo(u, tag="0.1.0")

    with cwd(tmpdir):
        c = get_test_config()

        pc = get_local_package_config(str(u))
        pc.upstream_project_url = str(u)
        lp = LocalProject(working_dir=str(u))

        ups = Upstream(c, pc, lp)

    new_ver = "1.2.3"
    ups.set_spec_version(version=new_ver, changelog_entry="- asdqwe")

    assert ups.get_specfile_version() == new_ver
    assert "%changelog" not in u.joinpath("beer.spec").read_text()


def change_source_ext(upstream, extension):
    preamble = upstream.specfile.spec_content.section("%package")
    for i, line in enumerate(preamble):
        if line.startswith("Source"):
            source = line.split()[1]
            start = line.index(source)
            source = source.rstrip("".join(Path(source).suffixes)) + extension
            preamble[i] = line[:start] + source
    upstream.specfile.save()


@pytest.mark.parametrize(
    "extension", [".tar.gz", ".tar.bz2"], ids=[".tar.gz", ".tar.bz2"]
)
def test_create_archive(upstream_instance, extension):
    u, ups = upstream_instance
    change_source_ext(ups, extension)

    ups.create_archive()

    assert u.glob(f"*{extension}")

    u.joinpath("README").write_text("\nEven better now!\n")
    subprocess.check_call(["git", "add", "."], cwd=u)
    subprocess.check_call(["git", "commit", "-m", "More awesome changes"], cwd=u)

    ups.create_archive()

    assert len(list(u.glob(f"*{extension}"))) == 2


def test_create_uncommon_archive(upstream_instance):
    u, ups = upstream_instance
    change_source_ext(ups, ".cpio")

    with pytest.raises(PackitException):
        ups.create_archive()


def test_fix_spec(upstream_instance):
    u, ups = upstream_instance

    ups.package_config.upstream_package_name = None
    with pytest.raises(PackitException) as ex:
        ups.fix_spec("asd.tar.gz", "1.2.3", "abcdef123")

    assert '"upstream_package_name" is not set' in str(ex.value)


def test_create_srpm(upstream_instance, tmpdir):
    u, ups = upstream_instance

    with pytest.raises(PackitException) as exc:
        ups.create_srpm()
    assert "Failed to create SRPM." == str(exc.value)

    ups.create_archive()
    srpm = ups.create_srpm()

    assert srpm.exists()

    srpm_path = Path(tmpdir).joinpath("custom.src.rpm")
    srpm = ups.create_srpm(srpm_path=srpm_path)
    assert srpm.exists()
    build_srpm(srpm)


def test_github_app(upstream_instance, tmpdir):
    u, ups = upstream_instance
    t = Path(tmpdir)

    fake_cert_path = t / "fake-cert.pem"
    fake_cert_path.write_text("hello!")

    user_config_file_path = t / ".packit.yaml"
    user_config_file_path.write_text(
        "---\n"
        f"authentication:\n"
        f"    github.com:\n"
        f"        github_app_private_key_path: {fake_cert_path}\n"
        f"        github_app_id: qwe\n"
    )
    flexmock(os).should_receive("getenv").with_args("XDG_CONFIG_HOME").and_return(
        str(tmpdir)
    )
    ups.config = Config.get_user_config()
    assert (
        GithubService(
            github_app_private_key_path=str(fake_cert_path), github_app_id="qwe"
        )
        in ups.config.services
    )
