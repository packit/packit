# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import flexmock
import pytest

from packit.patches import commit_message, remove_prefixes, PatchMetadata


@pytest.fixture
def patch(tmp_path):
    patch_file = tmp_path / "patch.patch"
    patch_file.write_text(
        """\
From 477fb1b17ee5fa84913102e964239c0d28019b8a Mon Sep 17 00:00:00 2001
From: =?UTF-8?q?Everyday=20Programmer?= <eprog@redhat.com>
Date: Wed, 18 Aug 2021 10:06:09 +0200
Subject: [PATCH 1/2] Add some content
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit

This is an explanation why the content was added.

Signed-off-by: Everyday Programmer <eprog@redhat.com>
---
 a.file | 1 +
 b.file | 1 +
 2 files changed, 2 insertions(+)

diff --git a/a.file b/a.file
index e69de29..8a1853f 100644
--- a/a.file
+++ b/a.file
@@ -0,0 +1 @@
+Some content in file A.
diff --git a/b.file b/b.file
index e69de29..e892e75 100644
--- a/b.file
+++ b/b.file
@@ -0,0 +1 @@
+Some content in file B.
--
2.31.1
"""
    )
    return patch_file


@pytest.fixture
def patch_with_meta(tmp_path):
    patch_file = tmp_path / "with_meta.patch"
    patch_file.write_text(
        """\
From 477fb1b17ee5fa84913102e964239c0d28019b8a Mon Sep 17 00:00:00 2001
From: =?UTF-8?q?Everyday=20Programmer?= <eprog@redhat.com>
Date: Wed, 18 Aug 2021 10:06:09 +0200
Subject: [PATCH 1/2] Add some content
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit

This is an explanation why the content was added.

Patch-name: clever.patch
Patch-id: 200
Patch-status: |
    # This needs to be here
Patch-present-in-specfile: true
Ignore-patch: true
No-prefix: true
Signed-off-by: Everyday Programmer <eprog@redhat.com>
---
 a.file | 1 +
 b.file | 1 +
 2 files changed, 2 insertions(+)

diff --git a/a.file b/a.file
index e69de29..8a1853f 100644
--- a/a.file
+++ b/a.file
@@ -0,0 +1 @@
+Some content in file A.
diff --git a/b.file b/b.file
index e69de29..e892e75 100644
--- a/b.file
+++ b/b.file
@@ -0,0 +1 @@
+Some content in file B.
--
2.31.1
"""
    )
    return patch_file


@pytest.fixture
def commit_message_file(tmp_path):
    file = tmp_path / "commit_message.file"
    file.write_text(
        """\
[PATCH 1/2] Add some content

This is an explanation why the content was added.

Signed-off-by: Everyday Programmer <eprog@redhat.com>
"""
    )
    return file


def test_remove_prefixes(patch):
    remove_prefixes(patch)
    assert (
        patch.read_text()
        == """\
From 477fb1b17ee5fa84913102e964239c0d28019b8a Mon Sep 17 00:00:00 2001
From: =?UTF-8?q?Everyday=20Programmer?= <eprog@redhat.com>
Date: Wed, 18 Aug 2021 10:06:09 +0200
Subject: [PATCH 1/2] Add some content
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit

This is an explanation why the content was added.

Signed-off-by: Everyday Programmer <eprog@redhat.com>
---
 a.file | 1 +
 b.file | 1 +
 2 files changed, 2 insertions(+)

diff --git a.file a.file
index e69de29..8a1853f 100644
--- a.file
+++ a.file
@@ -0,0 +1 @@
+Some content in file A.
diff --git b.file b.file
index e69de29..e892e75 100644
--- b.file
+++ b.file
@@ -0,0 +1 @@
+Some content in file B.
--
2.31.1
"""
    )


@pytest.mark.parametrize(
    "patch_file, strip_subject_prefix, strip_trailers",
    [
        ("patch", None, "Signed-off-by: Everyday Programmer <eprog@redhat.com>"),
        ("patch", "PATCH", None),
        (
            "commit_message_file",
            None,
            "Signed-off-by: Everyday Programmer <eprog@redhat.com>",
        ),
        ("commit_message_file", "PATCH", None),
    ],
)
def test_commit_message(patch_file, strip_subject_prefix, strip_trailers, request):
    file = request.getfixturevalue(patch_file)
    subject = f"{'' if strip_subject_prefix else '[PATCH 1/2] '}Add some content"
    body = f"""This is an explanation why the content was added.

{'' if strip_trailers else 'Signed-off-by: Everyday Programmer <eprog@redhat.com>'}
""".strip()
    assert (
        commit_message(
            file,
            strip_subject_prefix=strip_subject_prefix,
            strip_trailers=strip_trailers,
        )
        == f"{subject}\n\n{body}"
    )


@pytest.mark.parametrize(
    "patch_file, meta_fields",
    [
        (
            "patch",
            {
                "name": "patch.patch",
                "description": "Add some content\n\n"
                "This is an explanation why the content was added.",
            },
        ),
        (
            "patch_with_meta",
            {
                "name": "clever.patch",
                "description": "# This needs to be here",
                "present_in_specfile": True,
                "ignore": True,
                "patch_id": 200,
                "no_prefix": True,
                "metadata_defined": True,
            },
        ),
    ],
)
def test_from_patch(patch_file, meta_fields, request):
    patch_path = request.getfixturevalue(patch_file)
    assert PatchMetadata.from_patch(str(patch_path)) == PatchMetadata(
        path=patch_path, **meta_fields
    )


def test_from_git_trailers():
    commit = flexmock(
        message="""\
Add a test commit

Patch-name: test.patch
Signed-off-by: Everyday Programmer <eprog@redhat.com>
"""
    )
    patch_meta = PatchMetadata.from_git_trailers(commit)
    assert patch_meta.name == "test.patch"
