# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os.path
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import click
from osc import conf, core

from packit.cli.types import LocalProjectParameter
from packit.cli.utils import cover_packit_exception, get_packit_api, iterate_packages
from packit.config import get_context_settings, pass_config
from packit.config.aliases import DEPRECATED_TARGET_MAP
from packit.config.config import Config
from packit.config.package_config import PackageConfig
from packit.constants import (
    PACKAGE_LONG_OPTION,
    PACKAGE_OPTION_HELP,
    PACKAGE_SHORT_OPTION,
)

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
class Repository:
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
            return [XmlPathEntry(project=f"Fedora:EPEL:{version}", repository="stream")]
        if version in ("8", "7"):
            return [XmlPathEntry(project=f"Fedora:EPEL:{version}", repository="CentOS")]

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
    prj_name: str,
    description: Optional[str] = None,
) -> ET.Element:
    """Converts the list of packit targets (like `fedora-rawhide`) to a project
    meta xml configuration for the respective project in OBS.

    """
    repos: list[Repository] = []
    for target in targets:
        path = target_to_path(target)
        arch = target.split("-")[-1]
        name = target
        added = False

        for ind, repo in enumerate(repos):
            if repo.path == path:
                repos[ind] = Repository(
                    name=f"{repo.name}-{arch}",
                    path=path,
                    arch=[*repo.arch, arch],
                )
                added = True

        if not added:
            repos.append(Repository(name=name, path=path, arch=[arch]))

    root = ET.Element("project")
    root.attrib["name"] = prj_name

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


def create_package(prj_name: str, pkg_name: str) -> None:
    """Creates the package with the name ``pkg_name`` in the project
    ``prj_name`` on OBS. No sources are uploaded in the process.

    """
    (root := ET.Element("package")).attrib["name"] = pkg_name
    root.attrib["project"] = prj_name

    (title := ET.Element("title")).text = f"The {pkg_name} package"
    descr = ET.Element("description")

    root.append(title)
    root.append(descr)

    url = core.makeurl(_API_URL, ["source", prj_name, pkg_name, "_meta"])
    mf = core.metafile(url, ET.tostring(root))
    mf.sync()


@click.command("in-obs", context_settings=get_context_settings())
@click.option(
    "--owner",
    help="OBS user, owner of the project. (defaults to the username from the oscrc)",
)
@click.option(
    "--project",
    help="Project name to build in. It will be created if does not exist."
    " It defaults to home:$owner:packit:$pkg",
)
@click.option(
    "--targets",
    help="Comma separated list of chroots to build in. (defaults to 'fedora-rawhide-x86_64')",
    default="fedora-rawhide-x86_64",
)
@click.option(
    "--description",
    help="Description of the project to build in.",
    default=None,
)
@click.option(
    "--upstream-ref",
    default=None,
    help="Git ref of the last upstream commit in the current branch "
    "from which packit should generate patches "
    "(this option implies the repository is source-git).",
)
@click.option("--wait/--no-wait", default=True, help="Wait for the build to finish")
@click.option(
    PACKAGE_SHORT_OPTION,
    PACKAGE_LONG_OPTION,
    multiple=True,
    help=PACKAGE_OPTION_HELP.format(action="build"),
)
@click.argument("path_or_url", type=LocalProjectParameter(), default=os.path.curdir)
@pass_config
@cover_packit_exception
@iterate_packages
def obs(
    config: Config,
    owner: Optional[str],
    project: str,
    targets: str,
    description: Optional[str],
    upstream_ref: Optional[str],
    wait: bool,
    package_config: PackageConfig,
    path_or_url,
) -> None:
    api = get_packit_api(
        config=config,
        package_config=package_config,
        local_project=path_or_url,
    )

    conf.get_config()
    owner = owner or conf.config["api_host_options"][_API_URL]["user"]
    prj_name = project or f"home:{owner}:packit"

    targets_list = targets.split(",")
    for target in targets_list:
        if target in DEPRECATED_TARGET_MAP:
            logger.warning(
                f"Target '{target}' is deprecated. "
                f"Please use '{DEPRECATED_TARGET_MAP[target]}' instead.",
            )

    prj_meta = targets_to_project_meta(
        targets=targets_list,
        owner=owner,
        prj_name=prj_name,
        description=description,
    )

    url = core.makeurl(_API_URL, ["source", prj_name, "_meta"])
    mf = core.metafile(url, ET.tostring(prj_meta))
    mf.sync()

    pkg_names = list(package_config.packages.keys())

    if len(pkg_names) != 1:
        raise ValueError("Cannot handle multiple packages in package_config")

    create_package(prj_name, (pkg_name := pkg_names[0]))

    with TemporaryDirectory() as tmp_dir:
        core.Project.init_project(_API_URL, (prj_dir := Path(tmp_dir)), prj_name)

        (pkg_dir := (prj_dir / pkg_name)).mkdir()
        core.checkout_package(
            _API_URL,
            prj_name,
            pkg_name,
            prj_dir=prj_dir,
            pathname=pkg_dir,
        )

        pkg = core.Package(pkg_dir)

        for fname in filter(os.path.isfile, os.listdir(pkg_dir)):
            pkg.delete_file(fname)

        srpm = api.create_srpm(upstream_ref=upstream_ref, release_suffix="0")

        # don't use the files argument of unpack_srcrpm, it allows for shell
        # injection unless sanitized carefully
        core.unpack_srcrpm(str(srpm), pkg_dir)

        core.addFiles(
            [
                str(pkg_dir / fname)
                for fname in filter(os.path.isfile, os.listdir(pkg_dir))
            ],
        )

        pkg = core.Package(pkg_dir)
        msg = "Created by packit"
        if upstream_ref:
            msg += f" from upstream revision {upstream_ref}"
        pkg.commit(msg=msg)

        # wait for the build result
        if wait:
            core.get_results(_API_URL, prj_name, pkg_name, printJoin="", wait=True)
