# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import datetime
import os
import sys
import pytest
import textwrap

from flexmock import flexmock
from pkg_resources import DistributionNotFound, Distribution

from packit.api import get_packit_version
from packit.exceptions import PackitException, PackitLookasideCacheException, ensure_str
from packit.utils import sanitize_branch_name, sanitize_branch_name_for_rpm
from packit.utils.decorators import fallback_return_value
from packit.utils.repo import (
    get_namespace_and_repo_name,
    git_remote_url_to_https_url,
    git_patch_ish,
    get_metadata_from_message,
    get_message_from_metadata,
    get_commit_hunks,
)
from packit.utils.commands import run_command
from packit.utils.source_script import create_source_script
from packit.utils.upstream_version import requests, get_upstream_version
from packit.utils.lookaside import configparser, pyrpkg, get_lookaside_sources
from packit.utils.koji_helper import KojiHelper


@pytest.mark.parametrize(
    "url,namespace,repo_name",
    [
        ("https://github.com/org/name", "org", "name"),
        ("https://github.com/org/name/", "org", "name"),
        ("https://github.com/org/name.git", "org", "name"),
        ("git@github.com:org/name", "org", "name"),
        ("git@github.com:org/name.git", "org", "name"),
    ],
)
def test_get_ns_repo(url, namespace, repo_name):
    assert get_namespace_and_repo_name(url) == (namespace, repo_name)


def test_get_ns_repo_exc():
    url = "git@github.com"
    with pytest.raises(PackitException) as ex:
        get_namespace_and_repo_name(url)
    msg = f"Invalid URL format, can't obtain namespace and repository name: {url}"
    assert msg in str(ex.value)


@pytest.mark.parametrize("inp", ["/", None, ""])
def test_remote_to_https_invalid(inp):
    assert git_remote_url_to_https_url(inp) == ""


@pytest.mark.parametrize(
    "inp",
    [
        "https://github.com/packit/packit",
        "https://github.com/packit/packit.git",
        "http://github.com/packit/packit",
        "http://github.com/packit/packit.git",
        "http://www.github.com/packit/packit",
    ],
)
def test_remote_to_https_unchanged(inp):
    assert git_remote_url_to_https_url(inp) == inp


@pytest.mark.parametrize(
    "inp,ok",
    [
        ("git@github.com:packit/ogr", "https://github.com/packit/ogr"),
        (
            "ssh://ttomecek@pkgs.fedoraproject.org/rpms/alot.git",
            "https://pkgs.fedoraproject.org/rpms/alot.git",
        ),
        ("www.github.com/packit/packit", "https://www.github.com/packit/packit"),
        ("github.com/packit/packit", "https://github.com/packit/packit"),
        ("git://github.com/packit/packit", "https://github.com/packit/packit"),
        (
            "git+https://github.com/packit/packit.git",
            "https://github.com/packit/packit.git",
        ),
    ],
)
def test_remote_to_https(inp, ok):
    assert git_remote_url_to_https_url(inp) == ok


def test_run_command_w_env():
    run_command(["bash", "-c", "env | grep PATH"], env={"X": "Y"})


def test_get_packit_version_not_installed():
    flexmock(sys.modules["packit.api"]).should_receive("get_distribution").and_raise(
        DistributionNotFound
    )
    assert get_packit_version() == "NOT_INSTALLED"


def test_get_packit_version():
    flexmock(Distribution).should_receive("version").and_return("0.1.0")
    assert get_packit_version() == "0.1.0"


@pytest.mark.parametrize(
    "inp,exp",
    (("asd", "asd"), (b"asd", "asd"), ("🍺", "🍺"), (b"\xf0\x9f\x8d\xba", "🍺")),
    ids=("asd", "bytes-asd", "beer-str", "beer-bytes"),
)
def test_ensure_str(inp, exp):
    assert ensure_str(inp) == exp


@pytest.mark.parametrize(
    "to,from_,exp", (("/", "/", "."), ("/a", "/a/b", ".."), ("/a", "/c", "../a"))
)
def test_relative_to(to, from_, exp):
    assert os.path.relpath(to, from_) == exp


class TestFallbackReturnValue:
    @pytest.mark.parametrize(
        "raise_exception, decorator_exceptions",
        [
            pytest.param(ValueError, ValueError, id="raised"),
            pytest.param(ValueError, KeyError, id="raised"),
        ],
    )
    def test_fallback_return_value(self, raise_exception, decorator_exceptions):

        fallback_value = "test_fallback_value"

        @fallback_return_value(fallback_value, exceptions=decorator_exceptions)
        def simple_function(exc=None):
            """Simple test function."""
            if exc is not None:
                raise exc
            return 42

        # `except` accepts both single exception or tuple of exceptions, to make testing easier
        # we will transform also single exception to tuple
        decorator_exceptions = (
            decorator_exceptions
            if isinstance(decorator_exceptions, tuple)
            else (decorator_exceptions,)
        )

        if raise_exception:
            if raise_exception in decorator_exceptions:
                assert simple_function(raise_exception) == fallback_value
            elif raise_exception not in decorator_exceptions:
                with pytest.raises(raise_exception):
                    simple_function(raise_exception)

        elif not raise_exception:
            assert simple_function() == 42


@pytest.mark.parametrize(
    "inp,exp,exp_rpm",
    (("pr/123", "pr-123", "pr123"), ("🌈🌈🌈", "🌈🌈🌈", "🌈🌈🌈"), ("@#$#$%", "------", "")),
)
def test_sanitize_branch(inp, exp, exp_rpm):
    assert sanitize_branch_name(inp) == exp
    assert sanitize_branch_name_for_rpm(inp) == exp_rpm


@pytest.mark.parametrize(
    "inp,outp",
    [
        pytest.param(
            """
            """,
            """
            """,
            id="empty-patch",
        ),
        # There are some \t characters in the strings bellow,
        # and thats expected.
        pytest.param(
            textwrap.dedent(
                """
                Short description: NSCD must use nscd user.
                Author(s): Fedora glibc team <glibc@lists.fedoraproject.org>
                Origin: PATCH
                Upstream status: not-needed

                Fedora-specific configuration adjustment to introduce the nscd user.
                (Upstream does not assume this user exists.)

                diff -Nrup a/nscd/nscd.conf b/nscd/nscd.conf
                --- a/nscd/nscd.conf	2012-06-05 07:42:49.000000000 -0600
                +++ b/nscd/nscd.conf	2012-06-07 12:15:21.818318670 -0600
                @@ -33,7 +33,7 @@
                 #	logfile			/var/log/nscd.log
                 #	threads			4
                 #	max-threads		32
                -#	server-user		nobody
                +	server-user		nscd
                 #	stat-user		somebody
                    debug-level		0
                 #	reload-count		5
            """
            ),
            textwrap.dedent(
                """
                Short description: NSCD must use nscd user.
                Author(s): Fedora glibc team <glibc@lists.fedoraproject.org>
                Origin: PATCH
                Upstream status: not-needed

                Fedora-specific configuration adjustment to introduce the nscd user.
                (Upstream does not assume this user exists.)

                diff --git a/nscd/nscd.conf b/nscd/nscd.conf
                --- a/nscd/nscd.conf
                +++ b/nscd/nscd.conf
                @@ -33,7 +33,7 @@
                 #	logfile			/var/log/nscd.log
                 #	threads			4
                 #	max-threads		32
                -#	server-user		nobody
                +	server-user		nscd
                 #	stat-user		somebody
                    debug-level		0
                 #	reload-count		5
            """
            ),
            id="remove-timestamps",
        ),
        pytest.param(
            textwrap.dedent(
                """
                Short description: NSCD must use nscd user.
                Author(s): Fedora glibc team <glibc@lists.fedoraproject.org>
                Origin: PATCH
                Upstream status: not-needed

                Fedora-specific configuration adjustment to introduce the nscd user.
                (Upstream does not assume this user exists.)

                --- a/nscd/nscd.conf	2012-06-05 07:42:49.000000000 -0600
                +++ b/nscd/nscd.conf	2012-06-07 12:15:21.818318670 -0600
                @@ -33,7 +33,7 @@
                 #	logfile			/var/log/nscd.log
                 #	threads			4
                 #	max-threads		32
                -#	server-user		nobody
                +	server-user		nscd
                 #	stat-user		somebody
                    debug-level		0
                 #	reload-count		5
            """
            ),
            textwrap.dedent(
                """
                Short description: NSCD must use nscd user.
                Author(s): Fedora glibc team <glibc@lists.fedoraproject.org>
                Origin: PATCH
                Upstream status: not-needed

                Fedora-specific configuration adjustment to introduce the nscd user.
                (Upstream does not assume this user exists.)

                diff --git a/nscd/nscd.conf b/nscd/nscd.conf
                --- a/nscd/nscd.conf
                +++ b/nscd/nscd.conf
                @@ -33,7 +33,7 @@
                 #	logfile			/var/log/nscd.log
                 #	threads			4
                 #	max-threads		32
                -#	server-user		nobody
                +	server-user		nscd
                 #	stat-user		somebody
                    debug-level		0
                 #	reload-count		5
            """
            ),
            id="add-missing-diff",
        ),
    ],
)
def test_git_patch_ish(inp, outp):
    assert git_patch_ish(inp) == outp


@pytest.mark.parametrize(
    "source, result",
    [
        pytest.param("", None, id="empty message"),
        pytest.param("One sentence", None, id="one sentence"),
        pytest.param("One sentence\n", None, id="one sentence with end-line"),
        pytest.param(
            "One sentence\n\n", None, id="one sentence with multiple end-lines"
        ),
        pytest.param("One sentence\nSecond sentence\n", None, id="two sentences"),
        pytest.param("One sentence\nSecond sentence\n", None, id="two sentences"),
        pytest.param(
            "key: value",
            {"key": "value"},
            id="one key-value",
        ),
        pytest.param(
            "key: value\n",
            {"key": "value"},
            id="one key-value with empty-line",
        ),
        pytest.param(
            "key: value\nsecond_key: value",
            {"key": "value", "second_key": "value"},
            id="two key-values",
        ),
        pytest.param(
            "One sentence\nkey: value\n",
            {"key": "value"},
            id="one sentence and one key-value with empty-line",
        ),
        pytest.param(
            "Once sentence\nSecond sentence.\nkey: value",
            {"key": "value"},
            id="two sentences and one key-value",
        ),
        pytest.param(
            "Once sentence\n\nSecond sentence.\n\n\nkey: value",
            {"key": "value"},
            id="two sentences and one key-value with few empty lines",
        ),
        pytest.param(
            "Once sentence\nSecond sentence.\nkey: value\nother: key",
            {"key": "value", "other": "key"},
            id="two sentences and one key-value",
        ),
        pytest.param(
            "key: value\nsentence at the end",
            None,
            id="sentence at the end",
        ),
        pytest.param(
            "key: [a,b,c]",
            {"key": ["a", "b", "c"]},
            id="list as a value",
        ),
        pytest.param(
            "key:\n- a\n- b\n- c",
            {"key": ["a", "b", "c"]},
            id="list as a value in separate lines",
        ),
        pytest.param(
            "Sentence: with colon\nanother sentence without colon",
            None,
            id="colon in the sentence",
        ),
        pytest.param(
            "Sentence with colon: in the middle\nanother sentence without colon",
            None,
            id="colon in the sentence in the middle",
        ),
    ],
)
def test_get_metadata_from_message(source, result):
    assert get_metadata_from_message(commit=flexmock(message=source)) == result


@pytest.mark.parametrize(
    "metadata, header, result",
    [
        pytest.param({}, None, "", id="empty dict"),
        pytest.param({"key": "value"}, None, "key: value\n", id="single key-value"),
        pytest.param(
            {"key": "value", "other": "value"},
            None,
            "key: value\nother: value\n",
            id="multiple key-values",
        ),
    ],
)
def test_get_message_from_metadata(metadata, header, result):
    assert get_message_from_metadata(metadata, header) == result


@pytest.mark.parametrize(
    "ref, pr_id, merge_pr, target_branch, job_config_index, url, command",
    [
        (
            None,
            None,
            True,
            None,
            None,
            "https://github.com/packit/ogr",
            'packit -d prepare-sources --result-dir "$resultdir" --no-create-symlinks '
            "https://github.com/packit/ogr",
        ),
        (
            "123",
            None,
            True,
            None,
            None,
            "https://github.com/packit/ogr",
            'packit -d prepare-sources --result-dir "$resultdir" --ref 123 --no-create-symlinks '
            "https://github.com/packit/ogr",
        ),
        (
            None,
            "1",
            False,
            None,
            None,
            "https://github.com/packit/ogr",
            'packit -d prepare-sources --result-dir "$resultdir" --pr-id 1 '
            "--no-merge-pr --no-create-symlinks https://github.com/packit/ogr",
        ),
        (
            None,
            "1",
            True,
            "main",
            None,
            "https://github.com/packit/ogr",
            'packit -d prepare-sources --result-dir "$resultdir" --pr-id 1 '
            "--merge-pr --target-branch main --no-create-symlinks https://github.com/packit/ogr",
        ),
        (
            None,
            "1",
            True,
            "main",
            0,
            "https://github.com/packit/ogr",
            'packit -d prepare-sources --result-dir "$resultdir" --pr-id 1 '
            "--merge-pr --target-branch main --job-config-index 0 "
            "--no-create-symlinks https://github.com/packit/ogr",
        ),
    ],
)
def test_create_source_script(
    ref, pr_id, merge_pr, target_branch, job_config_index, url, command
):
    assert (
        create_source_script(
            ref=ref,
            pr_id=pr_id,
            merge_pr=merge_pr,
            target_branch=target_branch,
            job_config_index=job_config_index,
            url=url,
        )
        == f"""
#!/bin/sh

git config --global user.email "hello@packit.dev"
git config --global user.name "Packit"
resultdir=$PWD
{command}

"""
    )


def test_get_commit_hunks_single_change():
    commit = "abcdefgh"
    git_api = flexmock()
    git_api.should_receive("show").with_args(
        commit, format="", color="never"
    ).and_return(
        """\
diff --git a/test2 b/test2
deleted file mode 100644
index 1c7858b..0000000
--- a/test2
+++ /dev/null
@@ -1 +0,0 @@
-deleted
        """
    )
    repository = flexmock(git=git_api)
    hunks = get_commit_hunks(repository, commit)
    assert len(hunks) == 1
    assert "diff --git a/test2 b/test2" in hunks[0]
    assert "-deleted" in hunks[0]


def test_get_commit_hunks_multiple_changes():
    commit = "abcdefgh"
    git_api = flexmock()
    git_api.should_receive("show").with_args(
        commit, format="", color="never"
    ).and_return(
        """\
diff --git a/a b/a
new file mode 100644
index 0000000..7898192
--- /dev/null
+++ b/a
@@ -0,0 +1 @@
+a
diff --git a/b.txt b/b.txt
new file mode 100644
index 0000000..6178079
--- /dev/null
+++ b/b.txt
@@ -0,0 +1 @@
+b
        """
    )
    repository = flexmock(git=git_api)
    hunks = get_commit_hunks(repository, commit)
    assert len(hunks) == 2
    assert "diff --git a/a b/a" in hunks[0]
    assert "+a" in hunks[0]
    assert "diff --git a/b.txt b/b.txt" in hunks[1]
    assert "+b" in hunks[1]


@pytest.mark.parametrize(
    "package, version",
    [
        ("libtiff", "4.4.0"),
        ("tiff", "4.4.0"),
        ("python-specfile", "0.5.0"),
        ("specfile", "0.5.0"),
        ("python3-specfile", None),
        ("mock", "3.1-1"),
        ("packitos", "0.56.0"),
        ("packit", None),
    ],
)
def test_get_upstream_version(package, version):
    def mocked_get(url, params):
        packages = {
            "libtiff": "tiff",
            "python-specfile": "specfile",
            "mock": "mock",
        }
        projects = {
            "tiff": "4.4.0",
            "specfile": "0.5.0",
            "mock": "3.1-1",
            "packitos": "0.56.0",
        }
        if url.endswith("projects"):
            project, version = next(
                iter(
                    (k, v)
                    for k, v in projects.items()
                    if k.startswith(params["pattern"])
                ),
                (None, None),
            )
            items = [{"name": project, "version": version}] if project else []
            return flexmock(ok=True, json=lambda: {"projects": items})
        else:
            package_name = url.split("/")[-1]
            project = packages.get(package_name)
            version = projects.get(project)
            if version:
                return flexmock(ok=True, json=lambda: {"version": version})
        return flexmock(ok=False)

    flexmock(requests).should_receive("get").replace_with(mocked_get)

    assert get_upstream_version(package) == version


@pytest.mark.parametrize(
    "config, sources, package, result",
    [
        (
            {
                "lookaside": "https://src.fedoraproject.org/repo/pkgs",
                "lookaside_cgi": "https://src.fedoraproject.org/repo/pkgs/upload.cgi",
                "lookasidehash": "sha512",
            },
            [
                {
                    "file": "packitos-0.57.0.tar.gz",
                    "hash": "27e4f97e262d7b1eb0af79ef9ea8ceae"
                    "d024dfe7b3d7ca0141d63195e7a9d6ee"
                    "a147d8eef919cd7919435abc5b729ca0"
                    "4d9800a9df1c0334c6ca42a5747a8755",
                    "hashtype": "sha512",
                },
            ],
            "packit",
            [
                {
                    "path": "packitos-0.57.0.tar.gz",
                    "url": "https://src.fedoraproject.org/repo/pkgs"
                    "/packit/packitos-0.57.0.tar.gz/sha512/"
                    "27e4f97e262d7b1eb0af79ef9ea8ceae"
                    "d024dfe7b3d7ca0141d63195e7a9d6ee"
                    "a147d8eef919cd7919435abc5b729ca0"
                    "4d9800a9df1c0334c6ca42a5747a8755"
                    "/packitos-0.57.0.tar.gz",
                },
            ],
        ),
        (
            {
                "lookaside": "https://sources.stream.centos.org/sources",
                "lookaside_cgi": "https://sources.stream.rdu2.redhat.com/lookaside/upload.cgi",
                "lookasidehash": "sha512",
                "lookaside_namespaced": True,
            },
            [
                {
                    "file": "man-pages-5.10.tar.xz",
                    "hash": "a23f90136b0bf471f5ae3917ae0e558f"
                    "ec0671cace8ccdd8e244f41f11fefa4a"
                    "c0df84cf972cc20a1792d7b930db5e2c"
                    "451881c0937edabf7d5e1ec46c4760ed",
                    "hashtype": "sha512",
                },
                {
                    "file": "man-pages-additional-20140218.tar.xz",
                    "hash": "c7874db32a9bdefaea6c6be6549e6e65"
                    "38fa1d93260bf342dd0d9821fa05754a"
                    "a79a723e701493c81b2e1f460918429e"
                    "b9b5edb704b55878b1e5ed585a3ff07d",
                    "hashtype": "sha512",
                },
                {
                    "file": "man-pages-posix-2017-a.tar.xz",
                    "hash": "dac6bd5bb3e1d5f8918bad3eb15e08ee"
                    "b3e06ae160c04ccd5619bfb0c536139a"
                    "c06faa62b6856656a1bb9a7496f3148e"
                    "52a5227b83e4099be6e6b93230de211d",
                    "hashtype": "sha512",
                },
            ],
            "man-pages",
            [
                {
                    "path": "man-pages-5.10.tar.xz",
                    "url": "https://sources.stream.centos.org/sources"
                    "/rpms/man-pages/man-pages-5.10.tar.xz/sha512/"
                    "a23f90136b0bf471f5ae3917ae0e558f"
                    "ec0671cace8ccdd8e244f41f11fefa4a"
                    "c0df84cf972cc20a1792d7b930db5e2c"
                    "451881c0937edabf7d5e1ec46c4760ed"
                    "/man-pages-5.10.tar.xz",
                },
                {
                    "path": "man-pages-additional-20140218.tar.xz",
                    "url": "https://sources.stream.centos.org/sources"
                    "/rpms/man-pages/man-pages-additional-20140218.tar.xz/sha512/"
                    "c7874db32a9bdefaea6c6be6549e6e65"
                    "38fa1d93260bf342dd0d9821fa05754a"
                    "a79a723e701493c81b2e1f460918429e"
                    "b9b5edb704b55878b1e5ed585a3ff07d"
                    "/man-pages-additional-20140218.tar.xz",
                },
                {
                    "path": "man-pages-posix-2017-a.tar.xz",
                    "url": "https://sources.stream.centos.org/sources"
                    "/rpms/man-pages/man-pages-posix-2017-a.tar.xz/sha512/"
                    "dac6bd5bb3e1d5f8918bad3eb15e08ee"
                    "b3e06ae160c04ccd5619bfb0c536139a"
                    "c06faa62b6856656a1bb9a7496f3148e"
                    "52a5227b83e4099be6e6b93230de211d"
                    "/man-pages-posix-2017-a.tar.xz",
                },
            ],
        ),
        ({}, [], "test", []),
    ],
)
def test_get_lookaside_sources(config, sources, package, result):
    flexmock(
        configparser,
        ConfigParser=lambda: flexmock(
            read=lambda _: None, items=lambda _, **__: config
        ),
    )
    flexmock(
        pyrpkg.sources,
        SourcesFile=lambda *_: flexmock(entries=[flexmock(**s) for s in sources]),
    )
    if "lookaside" not in config:
        with pytest.raises(PackitLookasideCacheException):
            get_lookaside_sources("", package, "")
    else:
        assert get_lookaside_sources("", package, "") == result


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_koji_helper_get_builds(error):
    nvrs = [f"test-1.{n}-1.fc37" for n in range(3)]

    def getPackageID(*_, **__):
        return 12345

    def listBuilds(*_, **__):
        if error:
            raise Exception
        return [{"nvr": nvr} for nvr in nvrs]

    session = flexmock(getPackageID=getPackageID, listBuilds=listBuilds)
    result = KojiHelper(session).get_nvrs("test", datetime.datetime(2022, 6, 1))
    if error:
        assert result == []
    else:
        assert result == nvrs


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_koji_helper_get_latest_nvr_in_tag(error):
    nvr = "test-1.0-1.fc37"

    def listTagged(*_, **__):
        if error:
            raise Exception
        return [{"nvr": nvr}]

    session = flexmock(listTagged=listTagged)
    result = KojiHelper(session).get_latest_nvr_in_tag("test", "f37-updates-candidate")
    if error:
        assert result is None
    else:
        assert result == nvr


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_koji_helper_get_build_tags(error):
    tags = ["f37-updates-testing"]

    def listTags(*_, **__):
        if error:
            raise Exception
        return [{"name": t} for t in tags]

    session = flexmock(listTags=listTags)
    result = KojiHelper(session).get_build_tags("test-1.0-1.fc37")
    if error:
        assert result == []
    else:
        assert result == tags


@pytest.mark.parametrize(
    "error",
    [False, True],
)
def test_koji_helper_get_build_changelog(error):
    changelog = [
        (1655726400, "Nikola Forró <nforro@redhat.com> - 0.2-1.fc37", "- third entry"),
        (1652702400, "Nikola Forró <nforro@redhat.com> - 0.1-2.fc37", "- second entry"),
        (1648728000, "Nikola Forró <nforro@redhat.com> - 0.1-1.fc37", "- first entry"),
    ]

    def getRPMHeaders(*_, **__):
        if error:
            raise Exception
        result = list(zip(*changelog))
        return {
            "changelogtime": list(result[0]),
            "changelogname": list(result[1]),
            "changelogtext": list(result[2]),
        }

    session = flexmock(getRPMHeaders=getRPMHeaders)
    result = KojiHelper(session).get_build_changelog("test-0.2-1.fc37")
    if error:
        assert result == []
    else:
        assert result == changelog


@pytest.mark.parametrize(
    "since, formatted_changelog",
    [
        (
            1652702400,
            "* Mon Jun 20 2022 Nikola Forró <nforro@redhat.com> - 0.2-1\n"
            "- third entry\n",
        ),
        (
            1648728000,
            "* Mon Jun 20 2022 Nikola Forró <nforro@redhat.com> - 0.2-1\n"
            "- third entry\n"
            "\n"
            "* Mon May 16 2022 Nikola Forró <nforro@redhat.com> - 0.1-2\n"
            "- second entry\n",
        ),
        (
            0,
            "* Mon Jun 20 2022 Nikola Forró <nforro@redhat.com> - 0.2-1\n"
            "- third entry\n"
            "\n"
            "* Mon May 16 2022 Nikola Forró <nforro@redhat.com> - 0.1-2\n"
            "- second entry\n"
            "\n"
            "* Thu Mar 31 2022 Nikola Forró <nforro@redhat.com> - 0.1-1\n"
            "- first entry\n",
        ),
    ],
)
def test_koji_helper_format_changelog(since, formatted_changelog):
    changelog = [
        (1655726400, "Nikola Forró <nforro@redhat.com> - 0.2-1", "- third entry"),
        (1652702400, "Nikola Forró <nforro@redhat.com> - 0.1-2", "- second entry"),
        (1648728000, "Nikola Forró <nforro@redhat.com> - 0.1-1", "- first entry"),
    ]
    assert KojiHelper.format_changelog(changelog, since) == formatted_changelog


@pytest.mark.parametrize(
    "branch, tag",
    [
        ("f37", "f37-updates-candidate"),
        ("epel8", "epel8-testing-candidate"),
    ],
)
def test_koji_helper_get_candidate_tag(branch, tag):
    assert KojiHelper.get_candidate_tag(branch) == tag


@pytest.mark.parametrize(
    "tag, stable_tags",
    [
        ("f37-updates-candidate", ["f37-updates", "f37"]),
        ("f37-updates-testing", ["f37-updates", "f37"]),
        ("epel8-testing-candidate", ["epel8"]),
        ("epel8-testing", ["epel8"]),
        ("f37-updates", []),
        ("epel8", []),
        ("eln", []),
    ],
)
def test_koji_helper_get_stable_tags(tag, stable_tags):
    assert KojiHelper.get_stable_tags(tag) == stable_tags
