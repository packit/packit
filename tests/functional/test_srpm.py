# MIT License
#
# Copyright (c) 2019 Red Hat, Inc.

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
Functional tests for srpm command
"""
import json
from pathlib import Path

from packit.utils.commands import cwd
from tests.functional.spellbook import call_real_packit
from tests.spellbook import build_srpm


def test_srpm_command_for_path(upstream_or_distgit_path, tmp_path):
    with cwd(tmp_path):
        call_real_packit(parameters=["--debug", "srpm", str(upstream_or_distgit_path)])
        srpm_path = list(Path.cwd().glob("*.src.rpm"))[0]
        assert srpm_path.exists()
        build_srpm(srpm_path)


def test_srpm_command_for_path_with_multiple_sources(
    upstream_and_remote_with_multiple_sources,
):
    workdir, _ = upstream_and_remote_with_multiple_sources
    with cwd(workdir):
        call_real_packit(parameters=["--debug", "srpm", str(workdir)])
        srpm_path = list(Path.cwd().glob("*.src.rpm"))[0]
        assert srpm_path.exists()
        assert (Path.cwd() / "python-ogr.spec").exists()
        build_srpm(srpm_path)


def test_srpm_command(cwd_upstream_or_distgit):
    call_real_packit(parameters=["--debug", "srpm"], cwd=cwd_upstream_or_distgit)
    srpm_path = list(cwd_upstream_or_distgit.glob("*.src.rpm"))[0]
    assert srpm_path.exists()
    build_srpm(srpm_path)


def test_action_output(upstream_and_remote):
    upstream_repo_path = upstream_and_remote[0]
    packit_yaml_path = upstream_repo_path / ".packit.json"
    packit_yaml_dict = json.loads(packit_yaml_path.read_text())
    # http://www.atlaspiv.cz/?page=detail&beer_id=4187
    the_line_we_want = "MadCat - Imperial Stout Rum Barrel Aged 20°"
    packit_yaml_dict["actions"] = {
        "post-upstream-clone": [f"bash -c 'echo {the_line_we_want}'"]
    }
    packit_yaml_path.write_text(json.dumps(packit_yaml_dict))
    out = call_real_packit(
        parameters=["srpm"], cwd=upstream_repo_path, return_output=True
    )
    assert f"\n{the_line_we_want}\n" in out.decode()
    srpm_path = list(upstream_repo_path.glob("*.src.rpm"))[0]
    assert srpm_path.exists()
    build_srpm(srpm_path)


def test_srpm_spec_not_in_root(upstream_spec_not_in_root):
    call_real_packit(parameters=["--debug", "srpm"], cwd=upstream_spec_not_in_root[0])
    srpm_path = list(upstream_spec_not_in_root[0].glob("*.src.rpm"))[0]
    assert srpm_path.exists()
    build_srpm(srpm_path)


def test_srpm_weird_sources(upstream_and_remote_weird_sources):
    repo = upstream_and_remote_weird_sources[0]
    call_real_packit(parameters=["--debug", "srpm"], cwd=repo)
    srpm_path = list(repo.glob("*.src.rpm"))[0]
    assert srpm_path.exists()
    build_srpm(srpm_path)


def test_srpm_custom_path(cwd_upstream_or_distgit):
    custom_path = "sooooorc.rpm"
    call_real_packit(
        parameters=["--debug", "srpm", "--output", custom_path],
        cwd=cwd_upstream_or_distgit,
    )
    srpm_path = cwd_upstream_or_distgit.joinpath(custom_path)
    assert srpm_path.is_file()
    build_srpm(srpm_path)


def test_srpm_twice_with_custom_name(cwd_upstream_or_distgit):
    custom_path = "sooooorc.rpm"
    call_real_packit(
        parameters=["--debug", "srpm", "--output", custom_path],
        cwd=cwd_upstream_or_distgit,
    )
    srpm_path1 = cwd_upstream_or_distgit.joinpath(custom_path)
    assert srpm_path1.is_file()
    build_srpm(srpm_path1)

    custom_path2 = "sooooorc2.rpm"
    call_real_packit(
        parameters=["--debug", "srpm", "--output", custom_path2],
        cwd=cwd_upstream_or_distgit,
    )
    srpm_path2 = cwd_upstream_or_distgit.joinpath(custom_path2)
    assert srpm_path2.is_file()
    build_srpm(srpm_path2)


def test_srpm_twice(cwd_upstream_or_distgit):
    call_real_packit(parameters=["--debug", "srpm"], cwd=cwd_upstream_or_distgit)
    call_real_packit(parameters=["--debug", "srpm"], cwd=cwd_upstream_or_distgit)

    # since we build from the 0.1.0, we would get the same SRPM because of '--new 0.1.0'
    srpm_files = list(cwd_upstream_or_distgit.glob("*.src.rpm"))

    assert srpm_files[0].exists()

    build_srpm(srpm_files[0])


def _test_srpm_symlinking(upstream_repo_path, path_prefix):
    packit_yaml_path = upstream_repo_path / ".packit.json"
    packit_yaml_dict = json.loads(packit_yaml_path.read_text())

    sources_tarball = "random_sources.tar.gz"
    desired_path = f"{path_prefix}/tmp/{sources_tarball}"
    packit_yaml_dict["actions"] = {
        "create-archive": [
            f"bash -c 'mkdir tmp; touch {desired_path}; echo {desired_path}'"
        ]
    }
    packit_yaml_path.write_text(json.dumps(packit_yaml_dict))
    out = call_real_packit(
        parameters=["srpm"], cwd=upstream_repo_path, return_output=True
    )
    assert f"\n{desired_path}\n" in out.decode()

    srpm_path = list(upstream_repo_path.glob("*.src.rpm"))[0]
    assert srpm_path.exists()

    tarball = Path(upstream_repo_path / sources_tarball)
    # check if it's symlink
    assert tarball.is_symlink()
    # links to correct file
    assert (
        tarball.resolve() == (upstream_repo_path / f"tmp/{sources_tarball}").absolute()
    )


def test_srpm_symlinking_relative_path(upstream_and_remote):
    upstream_repo_path = upstream_and_remote[0]
    _test_srpm_symlinking(upstream_repo_path, ".")


def test_srpm_symlinking_absolute_path(upstream_and_remote):
    upstream_repo_path = upstream_and_remote[0]
    _test_srpm_symlinking(upstream_repo_path, upstream_repo_path)
