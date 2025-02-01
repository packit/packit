# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from osc import conf, core

from packit.config import PackageConfig
from packit.config.aliases import DEPRECATED_TARGET_MAP

logger = logging.getLogger(__name__)

_API_URL = "https://api.opensuse.org"


@dataclass(frozen=True)
class XmlPathEntry:
    """Representation of a path entry in the XML repository configuration of
    OBS.


    """

    project: str
    repository: str


@dataclass(frozen=True)
class OBSRepository:
    """Minimal representation of a repository on OBS that is part of the project
    meta configuration:

    .. code-block:: xml

       <repository name="images">
         <path project="openSUSE:Factory" repository="containerfile"/>
         <path project="openSUSE:Factory" repository="standard"/>
         <arch>x86_64</arch>
       </repository>

    """

    name: str
    arch: list[str]
    path: list[XmlPathEntry]


def target_to_path(target: str) -> list[XmlPathEntry]:
    """Converts a packit target name like ``fedora-rawhide-x86_64`` or
    ``opensuse-leap-15.5`` to a list of xml path entries of the respective
    projects on OBS. This function relies on the project setup on
    build.opensuse.org and is not directly re-usable on other OBS instances.

    """

    target_split = target.split("-")
    version, arch = target_split[-2:]
    distro = "-".join(target_split[:-2])

    if distro == "fedora":
        if version == "rawhide":
            return [XmlPathEntry(project="Fedora:Rawhide", repository="standard")]
        return [
            XmlPathEntry(project=f"Fedora:{version}", repository="standard"),
            XmlPathEntry(project=f"Fedora:{version}", repository="update"),
        ]

    if distro == "epel":
        if version == "9":
            return [
                XmlPathEntry(project=f"Fedora:EPEL:{version}", repository="stream"),
            ]
        if version in ("8", "7"):
            return [
                XmlPathEntry(project=f"Fedora:EPEL:{version}", repository="CentOS"),
            ]

    if distro == "opensuse-leap":
        return [
            XmlPathEntry(project=f"openSUSE:Leap:{version}", repository="standard"),
        ]

    if distro == "opensuse":
        if arch == "x86_64":
            return [XmlPathEntry(project="openSUSE:Factory", repository="snapshot")]
        if arch in ("s390x", "aarch64", "ppc64le"):
            postfix = {"s390x": "zSystem", "aarch64": "ARM", "ppc64le": "PowerPC"}[arch]
            return [
                XmlPathEntry(
                    project=f"openSUSE:Factory:{postfix}",
                    repository="standard",
                ),
            ]

    raise ValueError(f"No preset available for {distro=}, {version=}, {arch=}")


def targets_to_project_meta(
    targets: list[str],
    owner: str,
    project_name: str,
    description: Optional[str] = None,
) -> ET.Element:
    """Converts the list of packit targets (like `fedora-rawhide-x86_64`) to a project
    meta xml configuration for the respective project in OBS.

    """
    repos: list[OBSRepository] = []
    for target in targets:
        path = target_to_path(target)
        arch = target.split("-")[-1]
        name = target
        added = False

        for ind, repo in enumerate(repos):
            if repo.path == path:
                repos[ind] = OBSRepository(
                    name=f"{repo.name}-{arch}",
                    path=path,
                    arch=[*repo.arch, arch],
                )
                added = True

        if not added:
            repos.append(OBSRepository(name=name, path=path, arch=[arch]))

    root = ET.Element("project")
    root.attrib["name"] = project_name

    (title_elem := ET.Element("title")).text = "Packit project"
    (descr_elem := ET.Element("description")).text = description or ""
    (person_elem := ET.Element("person")).attrib["userid"] = owner
    person_elem.attrib["role"] = "maintainer"

    for elem in (title_elem, descr_elem, person_elem):
        root.append(elem)

    for repo in repos:
        (repo_elem := ET.Element("repository")).attrib["name"] = repo.name

        for path_entry in repo.path:
            (path_elem := ET.Element("path")).attrib["project"] = path_entry.project
            path_elem.attrib["repository"] = path_entry.repository
            repo_elem.append(path_elem)

        for arch in repo.arch:
            (arch_elem := ET.Element("arch")).text = arch
            repo_elem.append(arch_elem)

        root.append(repo_elem)

    return root


def parse_changelog_subject(line: str) -> tuple[list[str], list[str], str, str]:
    date: list[str]
    author: list[str] = []
    email: str = ""
    version: str = ""

    toks = [tok.strip() for tok in line.split(" ") if tok.strip()]

    toks.pop(0)  # Remove leading "*"
    date = toks[:4]

    del toks[:4]
    for index, element in enumerate(toks):
        if not element.startswith("<"):
            author.append(element)
        else:
            email += element
            del toks[: index + 1]
            break

    if toks and toks[0] == "-":
        toks.pop(0)

    if toks:
        version = toks[0]

    return date, author, email, version


def format_changelog(changelog_str: str) -> str:
    """Converts spec changelog to OBS .changes format"""
    output: list[str] = []
    changelog_time = "12:00:00 UTC"
    changelog = changelog_str.splitlines()

    version_pattern = re.compile(r"-\s[0-9]+[\.\-]*")  # Precompile regex

    for line in changelog:
        if not line.strip():
            continue
        if line.strip().startswith("*"):
            if output:
                output[-1] += "\n"

            date, author, email, version = parse_changelog_subject(line)
            date.insert(3, changelog_time)

            output.append("-" * 68)  # Set demarcator
            output.append(f"{' '.join(date)} - {' '.join(author)} {email}\n")
            if version:
                output.append(f"- {version}")
        else:
            if version_pattern.match(line):  # Match version line
                output.append(line)
            else:
                output.append(f"  {line}")

    return "\n".join(output)


def create_changes_file(package_dir: Path) -> None:
    """
    Creates a changelog file by copying the changelog section from the spec file.
    Sets release to 0 since obs handles release numbers

    Args:
        package_dir (Path): Path to the directory containing the package spec file.

    Returns:
        None
    """
    specfile: Optional[Path] = None
    release_line = "Release:    0"

    for file in package_dir.iterdir():
        if not file.is_file():
            continue

        if file.name.endswith(".spec"):
            specfile = file

        if file.name.endswith(".changes"):
            logger.info(".changes file already exists in package")
            return

    if not specfile:
        raise ValueError("Cannot find spec file in package")

    split_content = re.split(r"%changelog", specfile.read_text(), flags=re.IGNORECASE)
    if len(split_content) < 2:
        logger.info("Project has no changelog")
        return

    specfile_content, changes_file_content = split_content[0], "".join(
        split_content[1:],
    )

    with open(package_dir / specfile, "w") as s_file:
        specfile_content = "\n".join(
            [
                release_line if line.lower().startswith("release:") else line
                for line in specfile_content.splitlines()
            ],
        )
        s_file.write(specfile_content)

    changes_filename = package_dir / f"{specfile.name[:-5]}.changes"

    changes_filename.write_text(format_changelog(changes_file_content))


def create_package(project_name: str, package_name: str) -> None:
    """Creates the package with the name ``package_name`` in the project
    ``project_name`` on OBS. No sources are uploaded in the process.

    """
    (root := ET.Element("package")).attrib["name"] = package_name
    root.attrib["project"] = project_name

    (title := ET.Element("title")).text = f"The {package_name} package"
    descr = ET.Element("description")

    root.append(title)
    root.append(descr)

    package_url = core.makeurl(
        _API_URL,
        ["source", project_name, package_name, "_meta"],
    )
    metafile = core.metafile(package_url, ET.tostring(root))
    metafile.sync()


def create_obs_project(
    project: str,
    targets: str,
    owner: Optional[str],
    package_config: PackageConfig,
    description: Optional[str],
):
    """
    Creates a new OBS project and its associated package, ensuring only a single
    package is included per call.

    Args:
        project (str, optional): The desired name for the OBS project. Defaults to None.
        targets (str): Comma-separated list of build targets for the project. Defaults to "".
        owner (Optional[str], optional): The owner of the project. Defaults to None.
        package_config (PackageConfig): The config for the package to be included in the project.
        description (Optional[str], optional): A description for the project. Defaults to None.

    Returns:
        Tuple[str, str]: A tuple containing the created project name and associated package name.

    Raises:
        ValueError: If the provided package_config contains multiple packages.
    """
    conf.get_config()
    owner = owner or conf.config["api_host_options"][_API_URL]["user"]
    project_name = project or f"home:{owner}:packit"

    targets_list = targets.split(",")
    for target in targets_list:
        if target in DEPRECATED_TARGET_MAP:
            logger.warning(
                f"Target '{target}' is deprecated. "
                f"Please use '{DEPRECATED_TARGET_MAP[target]}' instead.",
            )

    project_metadata = targets_to_project_meta(
        targets=targets_list,
        owner=owner,
        project_name=project_name,
        description=description,
    )

    logger.info(f"Using OBS project name = {project_name}")

    project_url = core.makeurl(
        _API_URL,
        ["source", project_name, "_meta"],
    )
    metafile = core.metafile(project_url, ET.tostring(project_metadata))
    metafile.sync()

    package_names = list(package_config.packages.keys())

    if len(package_names) != 1:
        raise ValueError("Cannot handle multiple packages in package_config")

    create_package(project_name, (package_name := package_names[0]))

    return project_name, package_name


def init_obs_project(
    build_dir: str,
    package_name: str,
    project_name: str,
) -> Path:
    """
    Initializes an Open Build Service (OBS) project.

    Args:
        build_dir (str): Base directory for the project (local path).
        package_name (str): Name of the package to be built.
        project_name (str): Name of the OBS project to create.

    Returns:
        Path: Path to the empty package directory within the OBS project.
    """
    core.Project.init_project(
        _API_URL,
        (prj_dir := Path(build_dir)),
        project_name,
    )

    (pkg_dir := (prj_dir / package_name)).mkdir()
    core.checkout_package(
        _API_URL,
        project_name,
        package_name,
        prj_dir=prj_dir,
        pathname=pkg_dir,
    )

    pkg = core.Package(pkg_dir)

    for fname in os.listdir(pkg_dir):
        pkg.delete_file(fname)

    return pkg_dir


def commit_srpm_and_get_build_results(
    srpm: Path,
    project_name: str,
    package_name: str,
    package_dir: Path,
    upstream_ref: Optional[str],
    wait: bool,
):
    """
    Commits an SRPM and retrieves build results.

    This function unpacks the provided SRPM, and commits all files in the package_dir to OBS,
    and optionally waits for and retrieves the build results.

    Args:
        srpm (Path): Path to the SRPM file.
        project_name (str): Name of the OBS project the package belongs to.
        package_name (str): Name of the package.
        package_dir (Path): Path to the directory where the SRPM is unpacked.
        upstream_ref (Optional[str]): Git ref of the last upstream commit in the current branch
        from which packit should generate patches. Defaults to None.
        wait (bool, optional): Whether to wait for and retrieve build results. Defaults to True.

    Returns:
        None
    """
    # don't use the files argument of unpack_srcrpm, it allows for shell
    # injection unless sanitized carefully
    core.unpack_srcrpm(str(srpm), package_dir)

    create_changes_file(package_dir=package_dir)

    core.addFiles(
        [str(file_path) for file_path in package_dir.iterdir() if file_path.is_file()],
    )
    pkg = core.Package(package_dir)
    msg = "Created by packit"
    if upstream_ref:
        msg += f" from upstream revision {upstream_ref}"
    pkg.commit(msg=msg)

    # wait for the build result
    if wait:
        core.get_results(
            _API_URL,
            project_name,
            package_name,
            printJoin="",
            wait=True,
        )
