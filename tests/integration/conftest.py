# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import datetime
import io
import shutil
import subprocess
import tarfile
from collections.abc import Iterator
from pathlib import Path
from typing import Optional

import git
import pytest
from flexmock import flexmock
from gnupg import GPG
from ogr.abstract import PRStatus
from ogr.read_only import PullRequestReadOnly
from ogr.services.github import GithubProject, GithubService
from ogr.services.pagure import PagureProject, PagureService, PagureUser

from packit.api import PackitAPI
from packit.base_git import PackitRepositoryBase
from packit.cli.utils import get_packit_api
from packit.config import config, get_local_package_config
from packit.constants import FROM_SOURCE_GIT_TOKEN
from packit.distgit import DistGit
from packit.local_project import CALCULATE, LocalProject, LocalProjectBuilder
from packit.pkgtool import PkgTool
from packit.upstream import GitUpstream
from packit.utils.commands import cwd
from packit.utils.repo import create_new_repo
from tests.integration.utils import remove_gpg_key_pair
from tests.spellbook import (
    DATA_DIR,
    DISTGIT,
    NAME_VERSION,
    SOURCEGIT_SOURCEGIT,
    SOURCEGIT_UPSTREAM,
    TARBALL_NAME,
    UPSTREAM,
    get_test_config,
    git_add_and_commit,
    initiate_git_repo,
)

DOWNSTREAM_PROJECT_URL = "https://src.fedoraproject.org/not/set.git"
UPSTREAM_PROJECT_URL = "https://github.com/also-not/set.git"
SOURCE_GIT_RELEASE_TAG = "0.1.0"
HELLO_RELEASE = "1.0.1"


@pytest.fixture()
def mock_remote_functionality_upstream(upstream_and_remote, distgit_and_remote):
    u, _ = upstream_and_remote
    d, _ = distgit_and_remote
    return mock_remote_functionality(d, u)


@pytest.fixture()
def mock_remote_functionality_upstream_fast_forward_merge_branches(
    upstream_and_remote,
    distgit_and_remote,
):
    u, _ = upstream_and_remote
    d, _ = distgit_and_remote
    return mock_remote_functionality(d, u, fast_forward_merge_branch=True)


@pytest.fixture()
def mock_remote_functionality_downstream_autochangelog(
    upstream_and_remote,
    distgit_with_autochangelog_and_remote,
):
    u, _ = upstream_and_remote
    d, _ = distgit_with_autochangelog_and_remote
    return mock_remote_functionality(d, u)


@pytest.fixture()
def mock_remote_functionality_sourcegit(sourcegit_and_remote, distgit_and_remote):
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    return mock_remote_functionality(upstream=sourcegit, distgit=distgit)


def mock_spec_download_remote_s(
    repo_path: Path,
    spec_dir_path: Optional[Path] = None,
    archive_ref: str = "HEAD",
    files_to_create=None,
):
    files_to_create = files_to_create or []
    spec_dir_path = spec_dir_path or repo_path

    def mock_download_remote_sources(*_):
        """mock download of the remote archive and place it into dist-git repo"""

        archive_cmd = [
            "git",
            "archive",
            "--output",
            str(spec_dir_path / TARBALL_NAME),
            "--prefix",
            f"{NAME_VERSION}/",
            archive_ref,
        ]
        subprocess.check_call(archive_cmd, cwd=repo_path)
        for f in files_to_create:
            subprocess.check_call(["touch", f], cwd=repo_path)

    flexmock(PackitRepositoryBase, download_remote_sources=mock_download_remote_sources)


def mock_remote_functionality(
    distgit: Path,
    upstream: Path,
    fast_forward_merge_branch=False,
):
    example_pr = PullRequestReadOnly(
        title="",
        id=42,
        status=PRStatus.open,
        url="",
        description="",
        author="",
        source_branch="",
        target_branch="",
        created=datetime.datetime(1969, 11, 11, 11, 11, 11, 11),
    )

    def mocked_create_pr(*args, **kwargs):
        return example_pr

    release = flexmock(body="Some description of the upstream release", url="some-url")
    flexmock(config).should_receive("get_project").and_return(
        flexmock(
            get_release=lambda name, tag_name: release,
        ),
    )
    flexmock(GithubService)
    github_service = GithubService()
    flexmock(
        GithubService,
        get_project=lambda repo, namespace: GithubProject(
            "also-not",
            github_service,
            "set",
            github_repo=flexmock(),
        ),
    )
    flexmock(
        PagureProject,
        get_git_urls=lambda: {"git": DOWNSTREAM_PROJECT_URL},
        fork_create=lambda: None,
        get_fork=lambda: PagureProject("", "", PagureService()),
        create_pr=mocked_create_pr,
        default_branch="main",
    )
    if fast_forward_merge_branch:
        flexmock(PagureProject).should_receive("create_pr").times(2).and_return(
            example_pr,
        )
    flexmock(
        GithubProject,
        get_git_urls=lambda: {"git": UPSTREAM_PROJECT_URL},
        fork_create=lambda: None,
        get_release=lambda: flexmock(url="url"),
    )
    flexmock(PagureUser, get_username=lambda: "packito")

    dglp = LocalProjectBuilder().build(
        working_dir=distgit,
        git_repo=CALCULATE,
        git_url="https://packit.dev/rpms/beer",
        git_service=PagureService(),
    )
    flexmock(
        DistGit,
        push_to_fork=lambda *args, **kwargs: None,
        # let's not hammer the production lookaside cache webserver
        is_archive_in_lookaside_cache=lambda archive_path: False,
        local_project=dglp,
    )
    flexmock(DistGit).should_receive("existing_pr").and_return(None)

    def mocked_new_sources(sources=None, offline=False):
        sources = sources or []
        if not all(Path(s).is_file() for s in sources):
            raise RuntimeError("archive does not exist")

    flexmock(PkgTool, new_sources=mocked_new_sources)
    flexmock(PackitAPI, init_kerberos_ticket=lambda: None)
    return upstream, distgit


@pytest.fixture()
def mock_patching():
    flexmock(GitUpstream).should_receive("create_patches").and_return(["patches"])
    flexmock(DistGit).should_receive("specfile_add_patches").with_args(["patches"])


@pytest.fixture()
def cwd_upstream(upstream_and_remote) -> Iterator[Path]:
    upstream, _ = upstream_and_remote
    with cwd(upstream):
        yield upstream


@pytest.fixture()
def sourcegit_and_remote(tmp_path):
    sourcegit_remote = tmp_path / "source_git_remote"
    sourcegit_remote.mkdir()
    create_new_repo(sourcegit_remote, ["--bare"])

    sourcegit_dir = tmp_path / "source_git"
    shutil.copytree(SOURCEGIT_UPSTREAM, sourcegit_dir)
    initiate_git_repo(sourcegit_dir, tag=SOURCE_GIT_RELEASE_TAG)
    subprocess.check_call(
        ["cp", "-R", SOURCEGIT_SOURCEGIT, tmp_path],
        cwd=sourcegit_remote,
    )
    git_add_and_commit(directory=sourcegit_dir, message="sourcegit content")

    return sourcegit_dir, sourcegit_remote


@pytest.fixture()
def source_git_repo(sourcegit_and_remote):
    source_git_dir, _ = sourcegit_and_remote
    return git.Repo(source_git_dir)


@pytest.fixture()
def dist_git_repo(distgit_and_remote):
    dist_git_dir, _ = distgit_and_remote
    return git.Repo(dist_git_dir)


@pytest.fixture()
def hello_source_git_repo(tmp_path):
    repo_dir = tmp_path / "src" / "hello"
    shutil.copytree(DATA_DIR / "src" / "hello", repo_dir)
    repo = git.Repo.init(repo_dir)
    repo.git.add(".")
    repo.git.commit(message="Initial commit")
    repo.git.tag(HELLO_RELEASE)
    repo.create_remote("origin", "https://example.com/hello.git")
    return repo


@pytest.fixture()
def hello_dist_git_repo(tmp_path):
    repo_dir = tmp_path / "rpms" / "hello"
    shutil.copytree(DATA_DIR / "rpms" / "hello", repo_dir)
    repo = git.Repo.init(repo_dir)
    repo.git.add(".")
    repo.git.commit(message="Initial commit", author="Engin Eer <eer@redhat.com>")
    return repo


@pytest.fixture()
def downstream_n_distgit(tmp_path):
    d_remote = tmp_path / "downstream_remote"
    d_remote.mkdir()
    create_new_repo(d_remote, ["--bare"])

    d = tmp_path / "dist_git"
    shutil.copytree(DISTGIT, d)
    initiate_git_repo(d, tag="0.0.0")

    u = tmp_path / "upstream_git"
    shutil.copytree(UPSTREAM, u)
    initiate_git_repo(u, push=False, upstream_remote=str(d_remote))

    return u, d


@pytest.fixture()
def upstream_instance(upstream_and_remote, tmp_path):
    with cwd(tmp_path):
        u, _ = upstream_and_remote
        c = get_test_config()

        pc = get_local_package_config(str(u))
        pc.upstream_project_url = str(u)
        lp = LocalProjectBuilder().build(working_dir=u, git_repo=CALCULATE)

        ups = GitUpstream(c, pc, lp)
        yield u, ups


@pytest.fixture()
def upstream_instance_with_two_commits(upstream_instance):
    u, ups = upstream_instance
    new_file = u / "new.file"
    new_file.write_text("Some content")
    git_add_and_commit(u, message="Add new file")
    return u, ups


@pytest.fixture()
def distgit_instance(
    upstream_and_remote,
    distgit_and_remote,
    mock_remote_functionality_upstream,
):
    u, _ = upstream_and_remote
    d, _ = distgit_and_remote
    c = get_test_config()
    pc = get_local_package_config(str(u))
    pc.upstream_project_url = str(u)
    dg = DistGit(c, pc, clone_path=str(d))
    return d, dg


@pytest.fixture()
def distgit_instance_with_autochangelog(
    upstream_and_remote,
    distgit_with_autochangelog_and_remote,
    mock_remote_functionality_downstream_autochangelog,
):
    u, _ = upstream_and_remote
    d, _ = distgit_with_autochangelog_and_remote
    c = get_test_config()
    pc = get_local_package_config(str(u))
    pc.upstream_project_url = str(u)
    dg = DistGit(c, pc, clone_path=str(d))
    return d, dg


@pytest.fixture()
def api_instance(upstream_and_remote, distgit_and_remote):
    u, _ = upstream_and_remote
    d, _ = distgit_and_remote

    c = get_test_config()
    api = get_packit_api(
        config=c,
        local_project=LocalProjectBuilder().build(
            working_dir=Path.cwd(),
            git_repo=CALCULATE,
        ),
    )
    return u, d, api


def mock_api_for_source_git(
    sourcegit: Path,
    distgit: Path,
    up_local_project: LocalProject,
):
    with cwd(sourcegit):
        c = get_test_config()
        pc = get_local_package_config(
            package_config_path=sourcegit / ".distro" / "source-git.yaml",
        )
        pc.upstream_project_url = str(sourcegit)
        return PackitAPI(c, pc, up_local_project, dist_git_clone_path=str(distgit))


@pytest.fixture()
def api_instance_source_git(sourcegit_and_remote, distgit_and_remote):
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote
    builder = LocalProjectBuilder()
    up_lp = builder.build(working_dir=sourcegit, git_repo=CALCULATE)
    up_lp.git_project = (
        flexmock()
        .should_receive("get_release")
        .with_args(tag_name="0.1.0", name="0.1.0")
        .and_return(flexmock(url="some-url"))
        .mock()
    )
    return mock_api_for_source_git(sourcegit, distgit, up_lp)


def add_source_git_commit_trailer(api: PackitAPI):
    # The version in dg is different from up, sync it
    api.dg.specfile.version = api.up.specfile.expanded_version
    api.dg.commit(
        "Update spec",
        "",
        trailers=[
            (
                FROM_SOURCE_GIT_TOKEN,
                api.up.local_project.git_repo.head.commit.hexsha,
            ),
        ],
    )
    return api


@pytest.fixture()
def api_instance_update_source_git(api_instance_source_git):
    add_source_git_commit_trailer(api_instance_source_git)
    return api_instance_source_git


@pytest.fixture()
def api_instance_sync_push(sourcegit_and_remote, distgit_and_remote):
    sourcegit, _ = sourcegit_and_remote
    distgit, _ = distgit_and_remote

    repo = flexmock(
        default_branch="main",
        get_pulls=lambda state, sort, direction: [],
        fork="fork",
    )
    service = flexmock(user=flexmock(get_username=lambda: "packit"))
    up_lp = LocalProjectBuilder().build(
        working_dir=sourcegit,
        git_repo=CALCULATE,
        git_project=GithubProject(
            repo="beer",
            service=service,
            namespace="packit.dev",
            github_repo=repo,
        ),
    )
    api = mock_api_for_source_git(sourcegit, distgit, up_lp)

    add_source_git_commit_trailer(api)

    api.dg.specfile.version = "1.2.3"
    api.dg.commit("dist-git commit to be sync back", "")
    return api


@pytest.fixture()
def gnupg_instance() -> GPG:
    return GPG()


@pytest.fixture()
def private_gpg_key() -> str:
    """
    gnupg_instance.export_keys(key.fingerprint, secret=True, expect_passphrase=False)
    """

    return """-----BEGIN PGP PRIVATE KEY BLOCK-----

lQOYBFzRgy8BCADbrsCtPWqVWTNkl3U1LK3YWLnKiZIIMELv305s6Lfj8lTtFlAT
GXuIfalAqN18Rv6h+/aMXW872Gwk6Iv9hdkSF9e04YGqdrr7H/rw8976NogvhR73
aTi1BGh43AtFWifJy/MaSCVfy2gTeYqK17FHDnzqGunwQ4L0PQMvkscMOgmCQlPj
qF2WWiknku/aMeIoqAjUfIV3/dKVYPJH7g4QTo8U00CvfLSFMFhgzxW/nC+fPOh6
h7jXnXk2xvo+9rWPrPplUtjjuufjzxvz/azlB3PIR05tTRU27P2xI4rJBkZdzZ6t
67obFxImpRVJtV3kvyBPAja4k7x/mWQvC/dBABEBAAEAB/kB8DWKgcV4OmCB9XUn
CjUheMzw3MxhTp20lJ2SR+5hcECwE9eSh5HHt0YgSC0mHNE/2COJgwSJfGQd4kBj
9QOgjX3NfoTgnmoRb6uM5zXzMrp6YtwOVksWC8spL9XYn45E0UwckgDkarzJGTQv
++24QQg4n5KrWEkmQwiNaafgc3lyFf+xaCri2xlwMYdFqltROzrckHkcbjYFdASr
2dqoxGn79OdRhndg8+n1FA2UpQhI4fZyvQwkfO7x1Mjl3DxH97K6cvnW+KI0IlhE
2laZRowzqn8q8+zopWtFkhQmD/SV43eLfCbzyb0KKyAheH8zD6DS7Ij/KkcnLmTt
pMzxBADb0DkUb/mAArhzBDf4QBup+ryhuae9cPkhMlVKiegtojlmmsdTKgCxybFH
M33ITeNx84IvDTZCZkHFwyFWVXLTbQyIt7RsGOEYxbt7cI+SgmtvEdYtnf6Y1H7F
0WksC8ES4Z6BToQ4qeI5rd3QAk+qmQ4ZSA9iT7vDG8/9Wv0TKQQA/9kFB318C39+
m1W6m9/B482brEJqrGaAkFT4yOSjeo1C+n3b/iedCROwP44L1ifZT83uJ3ad/o/f
N5iDHiXjASVnIuuehLjuwrauZhkhiOcjRyLRtrDweF5NDQu70o69ON3j4fWebhmT
OFxfGaD9lkWuM2Lf0/0kbErc8X31nlkD/2tTepbT6y1ud2OrI9Fw4E8eKnSycJwW
JitKqllXkpugaEihBtpAf7zcarchnF2FIqnYuT5nVZ067lPKU5rRMuD3D+IXUxSy
aNgCSzVMX2t43DQcyZ35kqgLYOJwdc78tNtkNvbTkZBRDTpcdK69M6L+x+wMsHb1
PpLui3F4WAQ/Q2O0IUF1dG9nZW5lcmF0ZWQgS2V5IDxwYWNraXRAcGFja2l0PokB
TgQTAQgAOBYhBFvV9i+3z2ur7IY5eKtE1ItYjzIoBQJc0YMvAhsvBQsJCAcCBhUK
CQgLAgQWAgMBAh4BAheAAAoJEKtE1ItYjzIoaIQH/RQ47hZhyGz9vgD196KIUwTp
WLrJPVxNSd4mqx0lwE3B5T8xyboZHZoD5gNxFR/6CPs2Nh4fiyqjKzeU/t5W4Y3c
evyhgBJu9y4K1s7HHf+Sby0jlaeQyVs11Ngoul+CM2m6ZzlLyexEC8dUZ9fclDxb
TOQH3GkJ24vdkbZwN+KdL/AYtbRAvE2BwfK0EMg7ibRoh9Zfpc2hYLjBZ83yAKgY
FZ8bkeRu7lTdzpbTu/nEFKKDYusgbJuLBaW3GEjj726C/IHAp16QZI/SPKpt0cAK
YEWYFA0MxyZQhRqEDH2whr+QyWr5155N7kzHnUxbwos66sfcCmCH7iZHbN7q828=
=RSyl
-----END PGP PRIVATE KEY BLOCK-----
"""


@pytest.fixture()
def gnupg_key_fingerprint(gnupg_instance: GPG, private_gpg_key: str):
    keys_imported = gnupg_instance.import_keys(private_gpg_key)
    key_fingerprint = keys_imported.fingerprints[0]
    yield key_fingerprint

    if key_fingerprint in gnupg_instance.list_keys(secret=True).fingerprints:
        remove_gpg_key_pair(
            gpg_binary=gnupg_instance.gpgbinary,
            fingerprint=key_fingerprint,
        )


@pytest.fixture()
def upstream_without_config(tmp_path):
    u_remote = tmp_path / "upstream_remote"
    u_remote.mkdir()
    create_new_repo(u_remote, ["--bare"])

    return u_remote


@pytest.fixture
def create_archive():
    def create_archive_factory(output_path):
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode="w:gz") as tar:
            t = tarfile.TarInfo("dir1")
            t.type = tarfile.DIRTYPE
            tar.addfile(t)

        out.seek(0)
        with open(output_path, "bw") as archive:
            archive.write(out.read())

    return create_archive_factory
