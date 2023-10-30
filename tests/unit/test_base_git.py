# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import logging
from pathlib import Path
from typing import Optional, Union

import pytest
from distro import linux_distribution
from flexmock import flexmock
from specfile import Specfile
from specfile.changelog import ChangelogEntry

from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase, requests
from packit.command_handler import LocalCommandHandler
from packit.config import CommonPackageConfig, Config, PackageConfig, RunCommandType
from packit.config.sources import SourcesItem
from packit.distgit import DistGit
from packit.local_project import LocalProjectBuilder
from packit.upstream import Upstream
from packit.utils import commands
from tests.spellbook import can_a_module_be_imported


@pytest.fixture()
def distgit_with_actions():
    return DistGit(
        config=flexmock(Config()),
        package_config=flexmock(
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        downstream_package_name="beer",
                        actions={
                            ActionName.pre_sync: "command --a",
                            ActionName.get_current_version: "command --b",
                        },
                    ),
                },
            ),
        ),
    )


@pytest.fixture()
def upstream_with_actions():
    return Upstream(
        config=flexmock(Config()),
        package_config=flexmock(
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        actions={
                            ActionName.pre_sync: "command --a",
                            ActionName.get_current_version: "command --b",
                        },
                    ),
                },
            ),
        ),
        local_project=flexmock(
            repo_name=flexmock(),
            refresh_the_arguments=lambda: None,
            git_project=flexmock(),
            git_service=flexmock(),
        ),
    )


@pytest.fixture()
def packit_repository_base():
    return PackitRepositoryBase(
        config=Config(),
        package_config=PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    actions={
                        ActionName.pre_sync: "command --a",
                        ActionName.get_current_version: "command --b",
                    },
                ),
            },
        ),
    )


@pytest.fixture()
def packit_repository_base_more_actions():
    return PackitRepositoryBase(
        config=Config(),
        package_config=PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    actions={
                        ActionName.pre_sync: ["command --a", "command --a"],
                        ActionName.get_current_version: "command --b",
                    },
                ),
            },
        ),
    )


@pytest.fixture()
def packit_repository_base_with_sandcastle_object(tmp_path):
    c = Config()
    c.command_handler = RunCommandType.sandcastle
    b = PackitRepositoryBase(
        config=c,
        package_config=PackageConfig(
            packages={
                "package": CommonPackageConfig(
                    actions={
                        ActionName.pre_sync: "command -a",
                        ActionName.get_current_version: "command -b",
                    },
                ),
            },
        ),
    )
    b.local_project = LocalProjectBuilder().build(working_dir=Path("/sandcastle"))
    return b


def test_has_action_upstream(upstream_with_actions):
    assert upstream_with_actions.has_action(ActionName.pre_sync)
    assert not upstream_with_actions.has_action(ActionName.create_patches)


def test_has_action_distgit(distgit_with_actions):
    assert distgit_with_actions.has_action(ActionName.pre_sync)
    assert not distgit_with_actions.has_action(ActionName.create_patches)


def test_with_action_non_defined(packit_repository_base):
    if packit_repository_base.with_action(action=ActionName.create_patches):
        # this is the style we are using that function
        return

    raise AssertionError()


def test_with_action_defined(packit_repository_base):
    flexmock(commands).should_receive("run_command").once()

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    if packit_repository_base.with_action(action=ActionName.pre_sync):
        # this is the style we are using that function
        raise AssertionError()


def test_with_action_working_dir(packit_repository_base):
    flexmock(LocalCommandHandler).should_receive("run_command").with_args(
        command=["command", "--a"],
        env=None,
        print_live=True,
    ).and_return("command --a").once()

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    assert not packit_repository_base.with_action(action=ActionName.pre_sync)


def test_run_action_hook_not_defined(packit_repository_base):
    flexmock(commands).should_receive("run_command").times(0)

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    packit_repository_base.run_action(actions=ActionName.create_patches)


def test_run_action_not_defined(packit_repository_base):
    flexmock(LocalCommandHandler).should_receive("run_command").times(0)

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    action_method = (
        flexmock()
        .should_receive("action_function")
        .with_args("arg", kwarg="kwarg")
        .once()
        .mock()
        .action_function
    )
    packit_repository_base.run_action(
        ActionName.create_patches,
        action_method,
        {},
        "arg",
        kwarg="kwarg",
    )


def test_run_action_defined(packit_repository_base):
    flexmock(LocalCommandHandler).should_receive("run_command").with_args(
        command=["command", "--a"],
        env={},
        print_live=True,
    ).and_return("command --a").once()

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    action_method = (
        flexmock()
        .should_receive("action_function")
        .with_args("arg", kwarg="kwarg")
        .times(0)
        .mock()
        .action_function
    )

    packit_repository_base.run_action(
        ActionName.pre_sync,
        action_method,
        {},
        "arg",
        "kwarg",
    )


@pytest.mark.skipif(
    not can_a_module_be_imported("sandcastle"),
    reason="sandcastle is not installed",
)
def test_run_action_in_sandcastle(
    packit_repository_base_with_sandcastle_object,
    caplog,
):
    from sandcastle import Sandcastle

    flexmock(Sandcastle).should_receive("get_api_client").and_return(None).once()
    flexmock(Sandcastle).should_receive("run").and_return(None).once()

    def mocked_exec(
        command: list[str],
        env: Optional[dict] = None,
        cwd: Optional[Union[str, Path]] = None,
    ):
        if command == ["command", "-b"]:
            return "1.2.3"
        if command == ["command", "-a"]:
            return (
                "make po-pull\n"
                "make[1]: Entering directory "
                "'/sandcastle/docker-io-usercont-sandcastle-prod-20200820-160948197515'\n"
                "TEMP_DIR=$(mktemp --tmpdir -d anaconda-localization-XXXXXXXXXX)\n"
            )
        raise Exception("This command was not expected")

    flexmock(Sandcastle, exec=mocked_exec)
    flexmock(Sandcastle).should_receive("delete_pod").once().and_return(None)
    with caplog.at_level(logging.INFO, logger="packit"):
        packit_repository_base_with_sandcastle_object.run_action(
            ActionName.pre_sync,
            None,
            "arg1",
            "kwarg1",
        )
        packit_repository_base_with_sandcastle_object.run_action(
            ActionName.get_current_version,
            None,
            "arg2",
            "kwarg2",
        )
        # this is being called in PackitAPI.clean
        packit_repository_base_with_sandcastle_object.command_handler.clean()
        # leading space means that we have the output actually printed
        # and it's not a single line with the whole output
        assert " Running command: command -a on dir .\n" in caplog.text
        assert " make po-pull\n" in caplog.text
        assert " anaconda-localization-XXXXXXXXXX)\n" in caplog.text
        assert " 1.2.3\n" in caplog.text


@pytest.mark.skipif(
    not can_a_module_be_imported("sandcastle"),
    reason="sandcastle is not installed",
)
def test_command_handler_is_set(packit_repository_base_with_sandcastle_object):
    from sandcastle import Sandcastle

    flexmock(Sandcastle).should_receive("get_api_client").and_return(None).once()
    flexmock(Sandcastle).should_receive("run").and_return(None).once()

    # it's not set initially
    assert not packit_repository_base_with_sandcastle_object.is_command_handler_set()

    # and should be set once we invoke it
    assert packit_repository_base_with_sandcastle_object.command_handler.sandcastle
    assert packit_repository_base_with_sandcastle_object.is_command_handler_set()


def test_run_action_more_actions(packit_repository_base_more_actions):
    flexmock(LocalCommandHandler).should_receive("run_command").times(2)

    packit_repository_base_more_actions.local_project = flexmock(
        working_dir="my/working/dir",
    )

    action_method = (
        flexmock()
        .should_receive("action_function")
        .with_args("arg", kwarg="kwarg")
        .times(0)
        .mock()
        .action_function
    )
    packit_repository_base_more_actions.run_action(
        ActionName.pre_sync,
        action_method,
        "arg",
        kwarg="kwarg",
    )


def test_get_output_from_action_not_defined(packit_repository_base):
    flexmock(LocalCommandHandler).should_receive("run_command").times(0)

    packit_repository_base.local_project = flexmock(working_dir="my/working/dir")

    result = packit_repository_base.get_output_from_action(ActionName.create_patches)
    assert result is None


@pytest.mark.parametrize(
    "source, package_config, expected_urls, extra_source",
    [
        pytest.param(
            "https://download.samba.org/pub/rsync/src/rsync-3.1.3.tar.gz",
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="rsync.spec",
                        sources=[
                            SourcesItem(
                                path="rsync-3.1.3.tar.gz",
                                url="https://git.centos.org/sources/rsync/c8s/82e7829",
                            ),
                        ],
                    ),
                },
                jobs=[],
            ),
            ["https://git.centos.org/sources/rsync/c8s/82e7829"],
            False,
        ),
        pytest.param(
            "https://download.samba.org/pub/rsync/src/rsync-3.1.3.tar.gz",
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="rsync.spec",
                        sources=[
                            SourcesItem(
                                path="rsync-3.1.3.tar.gz",
                                url="https://git.centos.org/sources/rsync/c8s/82e7829",
                            ),
                        ],
                    ),
                },
                jobs=[],
            ),
            [
                "https://git.centos.org/sources/rsync/c8s/82e7829",
                "https://example.com/extra-source.tar.xz",
            ],
            True,
        ),
        pytest.param(
            "rsync-3.1.3.tar.gz",
            PackageConfig(
                packages={
                    "package": CommonPackageConfig(
                        specfile_path="rsync.spec",
                        sources=[
                            SourcesItem(
                                path="rsync-3.1.3.tar.gz",
                                url="https://git.centos.org/sources/rsync/c8s/82e7829",
                            ),
                        ],
                    ),
                },
                jobs=[],
            ),
            ["https://git.centos.org/sources/rsync/c8s/82e7829"],
            False,
        ),
    ],
)
def test_download_remote_sources(
    source,
    package_config,
    expected_urls,
    extra_source,
    tmp_path: Path,
):
    specfile_content = (
        "Name: rsync\n"
        "Version: 3.1.3\n"
        "Release: 1\n"
        f"Source0: {source}\n"
        "%if 0%{?extra_source}\n"
        "Source1: https://example.com/extra-source.tar.xz\n"
        "%endif\n"
        "License: GPLv3+\n"
        "Summary: rsync\n"
        "%description\nrsync\n"
    )
    spec_path = tmp_path / "rsync.spec"
    spec_path.write_text(specfile_content)
    specfile = Specfile(
        spec_path,
        sourcedir=tmp_path,
        autosave=True,
        macros=[("extra_source", "1")] if extra_source else None,
    )
    base_git = PackitRepositoryBase(config=flexmock(), package_config=package_config)
    flexmock(base_git).should_receive("specfile").and_return(specfile)

    expected_urls = iter(expected_urls)
    expected_path = tmp_path / "rsync-3.1.3.tar.gz"

    def mocked_get(url, **_):
        assert url == next(expected_urls)
        return flexmock(
            raise_for_status=lambda: None,
            iter_content=lambda **_: iter([b"1"]),
        )

    flexmock(requests).should_receive("get").replace_with(mocked_get)

    base_git.download_remote_sources()

    flexmock(requests).should_receive("get").and_raise(
        Exception(
            "This should not be called second time since the source is present already.",
        ),
    )
    base_git.download_remote_sources()

    assert expected_path.exists()


def test_set_spec_content(tmp_path):
    distgit_spec_contents = (
        "Name: bring-me-to-the-life\n"
        "Version: 1.0\n"
        "Release: 1\n"
        "Source0: foo.bar\n"
        "License: GPLv3+\n"
        "Summary: evanescence\n"
        "%description\n-\n\n"
        "%changelog\n"
        "* Mon Mar 04 2019 Foo Bor <foo-bor@example.com> - 1.0-1\n"
        "- Initial package.\n"
    )
    distgit_spec_path = tmp_path / "life.spec"
    distgit_spec_path.write_text(distgit_spec_contents)

    upstream_spec_contents = (
        "Name: bring-me-to-the-life\n"
        "Version: 1.0\n"
        "Release: 1\n"
        "Source0: foo.bor\n"
        "License: MIT\n"
        "Summary: evanescence, I was brought to life\n"
        "%description\n-\n"
        "%changelog\n"
        "* Mon Mar 04 2019 Foo Bor <foo-bor@example.com> - 1.0-1\n"
        "- Initial package.\n"
    )
    upstream_spec_path = tmp_path / "e-life.spec"
    upstream_spec_path.write_text(upstream_spec_contents)
    upstream_specfile = Specfile(upstream_spec_path, sourcedir=tmp_path, autosave=True)

    dist_git = PackitRepositoryBase(config=flexmock(), package_config=flexmock())
    dist_git._specfile_path = distgit_spec_path

    dist_git.set_specfile_content(upstream_specfile, None, None)
    with dist_git.specfile.sections() as sections:
        assert [
            "* Mon Mar 04 2019 Foo Bor <foo-bor@example.com> - 1.0-1",
            "- Initial package.",
        ] == sections.changelog
        assert dist_git.specfile.expanded_version == "1.0"
        assert "License: MIT" in sections.package
        assert "Summary: evanescence, I was brought to life" in sections.package

    new_log = ChangelogEntry(
        "* Wed Jun 02 2021 John Fou <john-fou@example.com> - 1.1-1",
        ["- 1.1 upstream release"],
    )
    flexmock(ChangelogEntry).should_receive("assemble").and_return(new_log)
    dist_git.set_specfile_content(upstream_specfile, "1.1", "1.1 upstream release")
    with dist_git.specfile.sections() as sections:
        assert [
            new_log.header,
            new_log.content[0],
            "* Mon Mar 04 2019 Foo Bor <foo-bor@example.com> - 1.0-1",
            "- Initial package.",
        ] == sections.changelog
    assert dist_git.specfile.expanded_version == "1.1"


@pytest.mark.parametrize(
    "dg_raw_version,dg_raw_release,up_raw_version,up_raw_release,expected_dg_release",
    [
        ("1.0", "2%{?dist}", "1.0", "2%{?dist}", "1"),
        ("1.0", "2%{?dist}", "1.0", "3%{?dist}", "1"),
        ("1.0", "2%{?dist}", "1.1", "2%{?dist}", "1"),
        ("1.0", "2%{?dist}", "1.1", "3%{?dist}", "3"),
        pytest.param(
            "1.0",
            "%autorelease",
            "1.0",
            "%autorelease",
            "%autorelease",
            marks=pytest.mark.skipif(
                linux_distribution()[0].startswith("CentOS"),
                reason="No rpmautospec-rpm-macros installed",
            ),
        ),
        pytest.param(
            "1.0",
            "%{autorelease}",
            "1.1",
            "%{autorelease}",
            "%{autorelease}",
            marks=pytest.mark.skipif(
                linux_distribution()[0].startswith("CentOS"),
                reason="No rpmautospec-rpm-macros installed",
            ),
        ),
        pytest.param(
            "1.0",
            "%autorelease -b 100",
            "1.1",
            "%autorelease -b 100",
            "%autorelease -b 100",
            marks=pytest.mark.skipif(
                linux_distribution()[0].startswith("CentOS"),
                reason="No rpmautospec-rpm-macros installed",
            ),
        ),
        pytest.param(
            "1.0",
            "%autorelease -p -e pre1",
            "1.0",
            "%autorelease",
            "%autorelease",
            marks=pytest.mark.skipif(
                linux_distribution()[0].startswith("CentOS"),
                reason="No rpmautospec-rpm-macros installed",
            ),
        ),
        pytest.param(
            "1.0",
            "2%{?dist}",
            "1.1",
            "%autorelease",
            "1",
            marks=pytest.mark.skipif(
                linux_distribution()[0].startswith("CentOS"),
                reason="No rpmautospec-rpm-macros installed",
            ),
        ),
        pytest.param(
            "1.0",
            "%autorelease",
            "1.1",
            "1%{?dist}",
            "%autorelease",
            marks=pytest.mark.skipif(
                linux_distribution()[0].startswith("CentOS"),
                reason="No rpmautospec-rpm-macros installed",
            ),
        ),
    ],
)
def test_set_spec_content_reset_release(
    tmp_path,
    dg_raw_version,
    dg_raw_release,
    up_raw_version,
    up_raw_release,
    expected_dg_release,
):
    def changelog(release):
        # %autorelease implies %autochangelog
        if "autorelease" in release:
            return "%autochangelog\n"
        return (
            "* Mon Mar 04 2019 Foo Bor <foo-bor@example.com> - 1.0-1\n"
            "- Initial package.\n"
        )

    distgit_spec_contents = (
        "Name: bring-me-to-the-life\n"
        f"Version: {dg_raw_version}\n"
        f"Release: {dg_raw_release}\n"
        "Source0: foo.bar\n"
        "License: GPLv3+\n"
        "Summary: evanescence\n"
        "%description\n-\n\n"
        "%changelog\n"
    ) + changelog(dg_raw_release)
    distgit_spec_path = tmp_path / "life.spec"
    distgit_spec_path.write_text(distgit_spec_contents)

    upstream_spec_contents = (
        "Name: bring-me-to-the-life\n"
        f"Version: {up_raw_version}\n"
        f"Release: {up_raw_release}\n"
        "Source0: foo.bor\n"
        "License: MIT\n"
        "Summary: evanescence, I was brought to life\n"
        "%description\n-\n"
        "%changelog\n"
    ) + changelog(up_raw_release)
    upstream_spec_path = tmp_path / "e-life.spec"
    upstream_spec_path.write_text(upstream_spec_contents)
    upstream_specfile = Specfile(upstream_spec_path, sourcedir=tmp_path, autosave=True)

    dist_git = PackitRepositoryBase(config=flexmock(), package_config=flexmock())
    dist_git._specfile_path = distgit_spec_path

    dist_git.set_specfile_content(upstream_specfile, "1.1", "1.1 upstream release")
    assert dist_git.specfile.release == expected_dg_release
    if not dist_git.specfile.has_autochangelog:
        with dist_git.specfile.sections() as sections:
            assert f"1.1-{expected_dg_release}" in sections.changelog[0]


@pytest.mark.parametrize("changelog_section", ["\n%changelog\n", ""])
def test_set_spec_content_no_changelog(tmp_path, changelog_section):
    distgit_spec_contents = (
        "Name: bring-me-to-the-life\n"
        "Version: 1.0\n"
        "Release: 1\n"
        "Source0: foo.bar\n"
        "License: GPLv3+\n"
        "Summary: evanescence\n"
        "%description\n-\n" + changelog_section
    )
    distgit_spec_path = tmp_path / "life.spec"
    distgit_spec_path.write_text(distgit_spec_contents)

    upstream_spec_contents = (
        "Name: bring-me-to-the-life\n"
        "Version: 1.0\n"
        "Release: 1\n"
        "Source0: foo.bor\n"
        "License: MIT\n"
        "Summary: evanescence, I was brought to life\n"
        "%description\n-\n"
        "%changelog\n"
        "* Mon Mar 04 2019 Foo Bor <foo-bor@example.com> - 1.0-1\n"
        "- Initial package.\n"
    )
    upstream_spec_path = tmp_path / "e-life.spec"
    upstream_spec_path.write_text(upstream_spec_contents)
    upstream_specfile = Specfile(upstream_spec_path, sourcedir=tmp_path, autosave=True)

    dist_git = PackitRepositoryBase(config=flexmock(), package_config=flexmock())
    dist_git._specfile_path = distgit_spec_path

    new_log = ChangelogEntry(
        "* Wed Jun 02 2021 John Fou <john-fou@example.com> - 1.1-1",
        ["- 1.1 upstream release"],
    )
    flexmock(ChangelogEntry).should_receive("assemble").and_return(new_log)
    dist_git.set_specfile_content(upstream_specfile, "1.1", "1.1 upstream release")
    with dist_git.specfile.sections() as sections:
        assert sections.changelog == [new_log.header, new_log.content[0]]


@pytest.mark.parametrize(
    "header, raw_version, macro_definitions",
    [
        pytest.param(
            "",
            "1.1",
            {},
        ),
        pytest.param(
            ("%global package_version 1.0\n"),
            "%{package_version}",
            {
                "package_version": "1.1",
            },
        ),
        pytest.param(
            (
                "%global majorver 1\n"
                "%global minorver 0\n"
                "%global package_version %{majorver}.%{minorver}\n"
            ),
            "%{package_version}",
            {
                "majorver": "1",
                "minorver": "1",
                "package_version": "%{majorver}.%{minorver}",
            },
        ),
        pytest.param(
            (
                "%global majorver 1\n"
                "%global minorver 0\n"
                "%global patchver 0\n"
                "%global package_version %{majorver}.%{minorver}.%{patchver}\n"
            ),
            "%{package_version}",
            {
                "majorver": "1",
                "minorver": "0",
                "patchver": "0",
                "package_version": "1.1",
            },
        ),
    ],
)
def test_set_spec_content_version_macros(
    tmp_path,
    header,
    raw_version,
    macro_definitions,
):
    distgit_spec_contents = header + (
        "Name: bring-me-to-the-life\n"
        "Version: %{package_version}\n"
        "Release: 1\n"
        "Source0: foo.bar\n"
        "License: GPLv3+\n"
        "Summary: evanescence\n"
        "%description\n-\n\n"
        "%changelog\n"
        "* Mon Mar 04 2019 Foo Bor <foo-bor@example.com> - 1.0-1\n"
        "- Initial package.\n"
    )
    distgit_spec_path = tmp_path / "life.spec"
    distgit_spec_path.write_text(distgit_spec_contents)

    upstream_spec_contents = header + (
        "Name: bring-me-to-the-life\n"
        "Version: %{package_version}\n"
        "Release: 1\n"
        "Source0: foo.bor\n"
        "License: MIT\n"
        "Summary: evanescence, I was brought to life\n"
        "%description\n-\n"
        "%changelog\n"
        "* Mon Mar 04 2019 Foo Bor <foo-bor@example.com> - 1.0-1\n"
        "- Initial package.\n"
    )
    upstream_spec_path = tmp_path / "e-life.spec"
    upstream_spec_path.write_text(upstream_spec_contents)
    upstream_specfile = Specfile(upstream_spec_path, sourcedir=tmp_path, autosave=True)

    dist_git = PackitRepositoryBase(config=flexmock(), package_config=flexmock())
    dist_git._specfile_path = distgit_spec_path

    new_log = ChangelogEntry(
        "* Wed Jun 02 2021 John Fou <john-fou@example.com> - 1.1-1",
        ["- 1.1 upstream release"],
    )
    flexmock(ChangelogEntry).should_receive("assemble").and_return(new_log)
    dist_git.set_specfile_content(upstream_specfile, "1.1", "1.1 upstream release")
    with dist_git.specfile.sections() as sections:
        assert [
            new_log.header,
            new_log.content[0],
            "* Mon Mar 04 2019 Foo Bor <foo-bor@example.com> - 1.0-1",
            "- Initial package.",
        ] == sections.changelog
    assert dist_git.specfile.expanded_version == "1.1"
    assert dist_git.specfile.version == raw_version
    with dist_git.specfile.macro_definitions() as mds:
        for md in mds:
            assert macro_definitions.pop(md.name) == md.body
    assert not macro_definitions
