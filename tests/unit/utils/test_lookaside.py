# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

from packit.exceptions import PackitLookasideCacheException
from packit.utils.lookaside import LookasideCache, configparser, pyrpkg


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
            read=lambda _: None,
            items=lambda _, **__: config,
        ),
    )
    flexmock(
        pyrpkg.sources,
        SourcesFile=lambda *_: flexmock(entries=[flexmock(**s) for s in sources]),
    )
    if "lookaside" not in config:
        with pytest.raises(PackitLookasideCacheException):
            LookasideCache("").get_sources("", package)
    else:
        assert LookasideCache("").get_sources("", package) == result
