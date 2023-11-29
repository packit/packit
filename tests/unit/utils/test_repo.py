# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import textwrap

import pytest
from flexmock import flexmock

from packit.constants import COMMIT_ACTION_DIVIDER
from packit.exceptions import PackitException
from packit.utils.repo import (
    get_commit_hunks,
    get_commit_link,
    get_commit_message_from_action,
    get_message_from_metadata,
    get_metadata_from_message,
    get_namespace_and_repo_name,
    get_tag_link,
    git_patch_ish,
    git_remote_url_to_https_url,
)


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
    "inp,with_suffix,result",
    [
        ("git@github.com:packit/ogr", True, "https://github.com/packit/ogr"),
        (
            "ssh://ttomecek@pkgs.fedoraproject.org/rpms/alot.git",
            True,
            "https://pkgs.fedoraproject.org/rpms/alot.git",
        ),
        ("www.github.com/packit/packit", True, "https://www.github.com/packit/packit"),
        ("github.com/packit/packit", True, "https://github.com/packit/packit"),
        ("git://github.com/packit/packit", True, "https://github.com/packit/packit"),
        (
            "git+https://github.com/packit/packit.git",
            True,
            "https://github.com/packit/packit.git",
        ),
        (
            "git+https://github.com/packit/packit.git",
            False,
            "https://github.com/packit/packit",
        ),
        (
            "https://github.com/packit/packit.git",
            False,
            "https://github.com/packit/packit",
        ),
    ],
)
def test_remote_to_https(inp, with_suffix, result):
    assert git_remote_url_to_https_url(inp, with_suffix) == result


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
            """,
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
            """,
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
            """,
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
            """,
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
            "One sentence\n\n",
            None,
            id="one sentence with multiple end-lines",
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


def test_get_commit_hunks_single_change():
    commit = "abcdefgh"
    git_api = flexmock()
    git_api.should_receive("show").with_args(
        commit,
        format="",
        color="never",
    ).and_return(
        """\
diff --git a/test2 b/test2
deleted file mode 100644
index 1c7858b..0000000
--- a/test2
+++ /dev/null
@@ -1 +0,0 @@
-deleted
        """,
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
        commit,
        format="",
        color="never",
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
        """,
    )
    repository = flexmock(git=git_api)
    hunks = get_commit_hunks(repository, commit)
    assert len(hunks) == 2
    assert "diff --git a/a b/a" in hunks[0]
    assert "+a" in hunks[0]
    assert "diff --git a/b.txt b/b.txt" in hunks[1]
    assert "+b" in hunks[1]


@pytest.mark.parametrize(
    "action_output",
    (
        pytest.param(
            None,
            id="no action defined",
        ),
        pytest.param(
            [],
            id="no output produced",
        ),
        pytest.param(
            # we keep a newline at the end of stdout, because we assume it's been
            # printed out and follows the convention of finishing with ‹\n›
            [
                "debug output\n",
                f"debug including divider\n{COMMIT_ACTION_DIVIDER}",
            ],
            id="nothing after divider",
        ),
        pytest.param(
            # we keep a newline at the end of stdout, because we assume it's been
            # printed out and follows the convention of finishing with ‹\n›
            [COMMIT_ACTION_DIVIDER],
            id="only divider",
        ),
        pytest.param(
            [COMMIT_ACTION_DIVIDER, "\n\n\n\n\n\ncommit body"],
            id="lot of newlines, no commit title",
        ),
    ),
)
def test_get_commit_message_from_action_default(action_output):
    # This test case contains only outputs that produce defaults
    title, body = get_commit_message_from_action(
        action_output,
        "default title",
        "default description",
    )

    assert title == "default title"
    assert body == "default description"


@pytest.mark.parametrize(
    "action_output, expected_title, expected_body",
    (
        pytest.param(
            ["debug\n", COMMIT_ACTION_DIVIDER, "commit title\n"],
            "commit title",
            "",
            id="only commit title given",
        ),
        pytest.param(
            ["debug\n", COMMIT_ACTION_DIVIDER, "commit title\n\ncommit body\n"],
            "commit title",
            "commit body",
            id="both title and body given",
        ),
        pytest.param(
            [COMMIT_ACTION_DIVIDER, "commit title\n"],
            "commit title",
            "",
            id="only commit title given; no debug messages",
        ),
        pytest.param(
            [COMMIT_ACTION_DIVIDER, "commit title\n\ncommit body\n"],
            "commit title",
            "commit body",
            id="both title and body given; no debug messages",
        ),
        pytest.param(
            ["commit title\n\n", "commit body\n"],
            "commit title",
            "commit body",
            id="both title and body given; no divider and debug output present",
        ),
        pytest.param(
            ["commit title\n"],
            "commit title",
            "",
            id="only commit title given; no divider and debug output present",
        ),
    ),
)
def test_get_commit_message_from_action(action_output, expected_title, expected_body):
    title, body = get_commit_message_from_action(
        action_output,
        "default title",
        "default description",
    )

    assert title == expected_title
    assert body == expected_body


@pytest.mark.parametrize(
    "git_url, commit, result",
    [
        pytest.param(
            "https://github.com/packit/packit-service",
            "abcdefg",
            "https://github.com/packit/packit-service/commit/abcdefg",
        ),
        pytest.param(
            "https://gitlab.com/packit/packit-service",
            "abcdefg",
            "https://gitlab.com/packit/packit-service/-/commit/abcdefg",
        ),
        pytest.param(
            "https://gitlab.gnome.org/packit/packit-service",
            "abcdefg",
            "https://gitlab.gnome.org/packit/packit-service/-/commit/abcdefg",
        ),
        pytest.param(
            "https://pagure.io/packit/packit-service",
            "abcdefg",
            "https://pagure.io/packit/packit-service/c/abcdefg",
        ),
    ],
)
def test_get_commit_link(git_url, commit, result):
    assert get_commit_link(git_url, commit) == result


@pytest.mark.parametrize(
    "git_url, tag, result",
    [
        pytest.param(
            "https://github.com/packit/packit-service",
            "1.0.0",
            "https://github.com/packit/packit-service/releases/tag/1.0.0",
        ),
        pytest.param(
            "https://gitlab.com/packit/packit-service",
            "1.0.0",
            "https://gitlab.com/packit/packit-service/-/tags/1.0.0",
        ),
        pytest.param(
            "https://gitlab.gnome.org/packit/packit-service",
            "1.0.0",
            "https://gitlab.gnome.org/packit/packit-service/-/tags/1.0.0",
        ),
        pytest.param("https://pagure.io/packit/packit-service", "1.0.0", ""),
    ],
)
def test_get_tag_link(git_url, tag, result):
    assert get_tag_link(git_url, tag) == result
