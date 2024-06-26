import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

from osc import core

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


class OBSHelper:
    _API_URL = "https://api.opensuse.org"

    @staticmethod
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
    @staticmethod
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
            path = OBSHelper.target_to_path(target)
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

    @staticmethod
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

        url = core.makeurl(OBSHelper._API_URL, ["source", prj_name, pkg_name, "_meta"])
        mf = core.metafile(url, ET.tostring(root))
        mf.sync()
