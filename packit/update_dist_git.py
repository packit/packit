# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import List, Optional

import git
import sys
import shutil
import tempfile
import rpm
import operator
import validators
import sh

from packit.config.package_config import get_local_package_config
from packit.config.config import Config
from packit.config.sources import SourcesItem
from packit.utils.repo import git_patch_ish
from packit.utils import download
from packit.patches import PatchGenerator, PatchMetadata


def patch_id_changed(repo: git.Repo, patch_path: str) -> bool:
    """Tell if the stable patch ID of <patch_path> changed between
    the version in HEAD and the current one.

    Arguments:
        repo: The repo in which the patch file is stored.
        patch_path: The path of the patch file relative to the repo root.

    Returns:
        True, if the patch ID changed, otherwise False.
    """
    # patch-id before the change
    prev_patch = repo.git.show(f"HEAD:{patch_path}")
    prev_patch = git_patch_ish(prev_patch)
    with tempfile.TemporaryFile(mode="w+") as fp:
        fp.write(prev_patch)
        fp.seek(0)
        prev_patch_id = repo.git.patch_id("--stable", istream=fp).split()[0]

    # current patch-id
    with open(Path(repo.working_dir) / Path(patch_path), "r") as fp:
        current_patch_id = repo.git.patch_id("--stable", istream=fp).split()[0]

    return current_patch_id != prev_patch_id


def purge_repo(repo: git.Repo, ignore: Optional[List[str]]):
    """Delete the files tracked in 'repo' from the working tree

    Do not delete the files listed in <ignore>.

    Arguments:
        repo: Git repo to purge.
        ignore: Optional list of file paths in the repo which should
            not be deleted.
    """
    working_dir = Path(repo.working_dir)
    for path in repo.git.ls_files().splitlines():
        if ignore and path in ignore:
            continue
        (working_dir / path).unlink()


def copy_git_repo_dir(repo: git.Repo, src_dir: str, dest_dir: Path):
    """Copy the content tracked by Git under <src_dir>, a subdirectory of <repo>,
    to <dest_dir>

    Arguments:
        repo: A Git repository.
        src_dir: A subdirectory tracked in <repo>.
        dest_dir: Directory where content from <src_dir> should be copied.
    """
    files = repo.git.ls_files(src_dir).splitlines()
    # First tell which subdirectories need to be created
    dirs = set()
    for file_ in files:
        dirs.add(dest_dir / Path(file_).parent.relative_to(src_dir))
    # Create those subdirectories
    for dir_ in dirs:
        dir_.mkdir(parents=True, exist_ok=True)
    # Copy the files
    repo_dir = Path(repo.working_dir)
    for file_ in files:
        shutil.copy2(repo_dir / file_, dest_dir / Path(file_).relative_to(src_dir))


def insert_patch_lines(
    specfile: Path,
    patches: List[PatchMetadata],
):
    """Insert patch lines in the spec-file

    Scan the spec-file, line-by-line, to tell where the last line starting
    with 'Source' is and insert Patch directives for each patch from
    patches after that.

    Arguments:
        specfile: Path of the spec-file to be updated.
        patches: List of patches for which a Patch directive is inserted.
    """
    if not patches:
        return

    spec_lines = specfile.read_text().splitlines()
    last_source_index = 0
    # Find the index of the last Source-line
    for index, line in enumerate(spec_lines):
        if line.startswith("Source"):
            last_source_index = index
    # Convert the patches list into lines of text
    patch_lines = []
    for index, patch in enumerate(patches, start=1):
        patch_lines += [f"# {line}" for line in patch.specfile_comment.splitlines()]
        patch_lines += [f"Patch{index:04d}: {patch.name}"]
        patch_lines += [""]
    # Update the spec-file lines with the patch lines just created
    until = last_source_index + 1
    from_ = until + 1 if not spec_lines[last_source_index + 1].strip() else until
    spec_lines = spec_lines[:until] + [""] + patch_lines + spec_lines[from_:]
    # Write everything back to the file
    specfile.write_text("\n".join(spec_lines) + "\n")


def download_source_archives(
    target: Path, config_sources: List[SourcesItem], specfile: Path
) -> List[str]:
    """Download source archives to the target path

    First: download the sources from the configured sources.
    Second: download all archives that are still not downloaded but are
    specified in Source directives in the spec-file.

    Arguments:
        target: Path were the source archives should be saved.
        config_sources: Source archives defined in the package configuration.
        specfile: Path to the spec-file for which sources archives are
            downloaded.
    Returns:
        List with the file names of the source archives that were downloaded.
    """
    downloaded = []
    # Download the source archives from config_sources
    for source in config_sources:
        download(source.url, target / source.path)
        downloaded.append(source.path)
    # Download the source archives mentioned in the spec-file
    # which are not yet downloaded
    spec = rpm.spec(str(specfile))
    spec_sources = [source for source in spec.sources if source[2] == 1]
    spec_sources = [
        source[0] for source in sorted(spec_sources, key=operator.itemgetter(1))
    ]
    spec_sources = [source for source in spec_sources if validators.url(source)]
    for source_url in spec_sources:
        file_name = Path(source_url).name
        source_path = target / file_name
        if not source_path.exists():
            download(source_url, source_path)
            downloaded.append(file_name)
    return downloaded


def update_dist_git(
    source_git: Path,
    dist_git: Path,
    config: Config,
    pkg_tool: Optional[str] = None,
    message: Optional[str] = None,
):
    """Update a dist-git repo from a source-git repo

    This does the following:
    - read the package configuration in the source-git repo to tell
      the upstream_ref
    - purge tracked files from the dist-git repo to prepare it for
      the update
    - copy the content of .distro to the dist-git repo
    - generate the patch files since upstream_ref and save them to
      the dist-git repo
    - update the spec-file with these patches by inserting patch lines
      after all the sources are defined
    - download the source archives and upload them to the lookaside
      cache if a packaging tool is defined
    - commit all the changes in the dist-git repo if a message is
      provided

    Arguments:
        source_git: Path of the source-git repository from which updates
            are taken.
        dist_git: Path of the dist-git repository to be updated.
        config: Packit configuration options from the command line.
        pkg_tool: Name of the pkg_tool to be used to save source archives
            in the lookaside cache.
        message: Commit message of the dist-git commit.
            Do not commit if this is empty or none.
    """
    # Make sure, both of these are absolute paths, in order to avoid
    # complications with relative paths in the lines that follow.
    # Without this one would need to remember to calculate 'relative_to'
    # paths when commands running in one of the repos needs to output to
    # the other repo (relative_to calculation which would require resolving
    # the absolute paths first, anyways).
    source_git = source_git.resolve()
    dist_git = dist_git.resolve()

    source_git_repo = git.Repo(source_git)
    dist_git_repo = git.Repo(dist_git)
    # make the dist-git working directory empty
    purge_repo(dist_git_repo, ignore=[".git", ".gitignore", "sources"])
    # copy files from the .distro directory to dist-git
    copy_git_repo_dir(source_git_repo, ".distro", dist_git)
    # get the upstream ref
    package_config = get_local_package_config(
        source_git, package_config_path=config.package_config_path
    )
    upstream_ref = package_config.upstream_ref
    # create patch files in dist_git
    patch_generator = PatchGenerator(source_git_repo)
    patches = patch_generator.create_patches(
        upstream_ref, str(dist_git), files_to_ignore=[".distro", ".packit.yaml"]
    )
    PatchGenerator.undo_identical(patches, dist_git_repo)
    # update spec file
    specfile = dist_git / (dist_git.resolve().name + ".spec")
    if patches:
        insert_patch_lines(specfile, patches)
    # Download the source archives and upload them to the lookaside cache.
    # Do this only if there is a packaging tool defined, as this tool is responsible
    # to update the sources file and .gitignore with the archives and upload them
    # to the lookaside cache.
    # Authentication for the packaging tool to work is not handled by this code, so it
    # falls upon the user.
    if pkg_tool:
        # 💣
        # So this is problematic.
        # Sources are downloaded in the dist-git dir, but there should be a clean-up first,
        # to make sure that the archives are the latest ones.
        # One approach is to delete all archives mentioned in 'sources'.
        source_archives = download_source_archives(
            dist_git, package_config.sources, specfile
        )
        if source_archives:
            pkg_tool_cmd = sh.Command(pkg_tool)
            pkg_tool_cmd(
                "new-sources",
                *source_archives,
                _out=sys.stdout,
                _err=sys.stderr,
                _cwd=dist_git,
            )
    # add and commit everything
    dist_git_repo.git.add(".")
    if message:
        # Take a note of the range of commits in the commit message.
        # Make sure the subject line is followed by an empty line.
        new_line = "\n" if not message.count("\n") else ""
        message = f"""{message}{new_line}
        Source-git-range: {upstream_ref}..{source_git_repo.head.commit}
        """
        dist_git_repo.git.commit("-m", message)
