# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path
from contextlib import contextmanager

import pytest

# from flexmock import flexmock

from packit.sync import check_subpath, SyncFilesItem
from packit.exceptions import PackitException


@contextmanager
def return_result(result):
    yield result


@pytest.mark.parametrize(
    "subpath,path,trailing_slash,result",
    [
        (
            Path("./test/this"),
            Path("."),
            False,
            return_result(str(Path("./test/this").resolve())),
        ),
        (
            Path("test/this"),
            Path("."),
            False,
            return_result(str(Path("test/this").resolve())),
        ),
        (
            Path("test/this"),
            Path("."),
            True,
            return_result(str(Path("test/this").resolve()) + "/"),
        ),
        (Path("../test/this"), Path("."), False, pytest.raises(PackitException)),
        (Path("test/../../this"), Path("."), False, pytest.raises(PackitException)),
    ],
)
def test_check_subpath(subpath, path, trailing_slash, result):
    with result as r:
        assert check_subpath(subpath, path, trailing_slash) == r


@pytest.mark.parametrize(
    "item,drop,result",
    [
        (SyncFilesItem(["a", "b"], "dest"), {"src": "b"}, SyncFilesItem(["a"], "dest")),
        (SyncFilesItem(["a"], "dest"), {"src": Path("a")}, None),
        (
            SyncFilesItem(["a", "b"], "dest"),
            {"src": "c"},
            SyncFilesItem(["a", "b"], "dest"),
        ),
        (
            SyncFilesItem(["src/a", "src/b"], "dest"),
            {"src": "a", "criteria": lambda x, y: Path(x).name == y},
            SyncFilesItem(["src/b"], "dest"),
        ),
    ],
)
def test_drop_src(item, drop, result):
    """Check dropping a item from the src-list

    The 'src' argument can be a string or Path.
    When used in 'criteria' as 'y', there is no type conversion,
    so if the caller defines a custem 'criteria', it falls on them,
    to make sure the types of 'src' and 'y' match.
    """
    assert result == item.drop_src(**drop)


@pytest.mark.parametrize(
    "item,args,result",
    [
        (
            SyncFilesItem(["a", "b"], "dest"),
            {},
            return_result(
                SyncFilesItem(
                    [Path(Path.cwd() / "a"), Path(Path.cwd() / "b")],
                    Path(Path.cwd() / "dest"),
                )
            ),
        ),
        (
            SyncFilesItem(["a", "b"], "dest"),
            {"src_base": Path("src").resolve(), "dest_base": Path("dest")},
            return_result(
                SyncFilesItem(
                    [Path(Path.cwd() / "src" / "a"), Path(Path.cwd() / "src" / "b")],
                    Path(Path.cwd() / "dest" / "dest"),
                )
            ),
        ),
        (
            SyncFilesItem(["../a", "b"], "dest"),
            {"src_base": Path("src"), "dest_base": Path("dest").resolve()},
            pytest.raises(PackitException),
        ),
    ],
)
def test_resolve(item, args, result):
    with result as r:
        item.resolve(**args)
        assert r == item


@pytest.mark.parametrize(
    "item,args,result",
    [
        (
            SyncFilesItem(["a", "b"], "dest"),
            {},
            ["rsync", "--archive", "--ignore-missing-args", "a", "b", "dest"],
        ),
        (
            SyncFilesItem(["a", "b"], "dest2"),
            {"fail_on_missing": True},
            ["rsync", "--archive", "a", "b", "dest2"],
        ),
        (
            SyncFilesItem(["c", "d"], "dest", mkpath=True, delete=True),
            {},
            [
                "rsync",
                "--archive",
                "--delete",
                "--mkpath",
                "--ignore-missing-args",
                "c",
                "d",
                "dest",
            ],
        ),
        (
            SyncFilesItem(["c/*"], "dest", mkpath=True),
            {},
            ["rsync", "--archive", "--mkpath", "--ignore-missing-args", "c/*", "dest"],
        ),
        (
            SyncFilesItem(
                ["src/"],
                "dest",
                delete=True,
                filters=["protect .git*", "protect sources"],
            ),
            {"fail_on_missing": True},
            [
                "rsync",
                "--archive",
                "--delete",
                "--filter",
                "protect .git*",
                "--filter",
                "protect sources",
                "src/",
                "dest",
            ],
        ),
    ],
)
def test_command(item, args, result):
    assert result == item.command(**args)


def test_command_globs(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "file1").touch()
    (src_dir / "file2").touch()
    item = SyncFilesItem(["src/*"], "dest")
    item.resolve(src_base=tmp_path, dest_base=tmp_path)
    command = item.command()
    # The return value of glob.glob() is unordered
    command = command[:-3] + sorted(command[-3:-1]) + command[-1:]
    assert [
        "rsync",
        "--archive",
        "--ignore-missing-args",
        f"{tmp_path}/src/file1",
        f"{tmp_path}/src/file2",
        f"{tmp_path}/dest",
    ] == command


def test_sync_files_item_sorting():
    order1 = [
        SyncFilesItem(src=["packit.spec"], dest="packit.spec"),
        SyncFilesItem(src=[".packit.yaml"], dest=".packit2.yaml"),
    ]
    order2 = [
        SyncFilesItem(src=[".packit.yaml"], dest=".packit2.yaml"),
        SyncFilesItem(src=["packit.spec"], dest="packit.spec"),
    ]
    assert sorted(order1) == sorted(order2)
