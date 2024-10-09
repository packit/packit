# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from copr.v3 import (
    BuildProxy,
    Client,
    CoprAuthException,
    ProjectProxy,
)
from flexmock import flexmock
from munch import munchify

import packit
from packit.api import PackitAPI
from packit.config import PackageConfig
from packit.copr_helper import CoprHelper
from packit.exceptions import (
    PackitCoprException,
    PackitCoprProjectException,
    PackitCoprSettingsException,
)
from tests.spellbook import run_packit


def test_copr_build_existing_project(cwd_upstream_or_distgit, api_instance):
    u, d, api = api_instance
    owner = "the-owner"
    project = "project-name"
    description = "some description"
    instructions = "the instructions"
    chroots = ["fedora-rawhide-x86_64"]

    flexmock(ProjectProxy).should_receive("add").and_return(
        flexmock(
            chroot_repos=flexmock(keys=lambda: chroots),
            description=description,
            instructions=instructions,
            unlisted_on_hp=True,
            delete_after_days=60,
            additional_repos=[],
            ownername=owner,
            module_hotfixes=False,
        ),
    )

    # no change in settings => no edit
    flexmock(ProjectProxy).should_receive("edit").times(0)

    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(config={"copr_url": "https://copr.fedorainfracloud.org"}),
    )

    build = flexmock(
        id="1",
        ownername=owner,
        projectname=project,
    )
    flexmock(BuildProxy).should_receive("create_from_file").and_return(build)
    build_id, url = api.run_copr_build(
        project=project,
        owner=owner,
        chroots=chroots,
        description=description,
        instructions=instructions,
    )

    assert build_id == "1"
    assert url == f"https://copr.fedorainfracloud.org/coprs/build/{build.id}/"


def test_copr_build_existing_project_change_settings(
    cwd_upstream_or_distgit,
    api_instance,
):
    u, d, api = api_instance
    owner = "the-owner"
    project = "project-name"
    description = "some description"
    instructions = "the instructions"
    chroots = ["fedora-rawhide-x86_64"]

    flexmock(ProjectProxy).should_receive("add").and_return(
        flexmock(
            chroot_repos=flexmock(keys=lambda: chroots),
            description=description,
            instructions=instructions,
            unlisted_on_hp=True,
            delete_after_days=60,
            additional_repos=[],
            ownername=owner,
            module_hotfixes=False,
        ),
    )

    flexmock(ProjectProxy).should_receive(
        "edit",
        # ).with_args(
        # ownername="the-owner",
        # projectname="project-name",
        # chroots=["fedora-rawhide-x86_64"],
        # description="different description",
        # instructions="the instructions",
        # unlisted_on_hp=True,
        # additional_repos=None,
        # delete_after_days=60,
        #
        # Does not work:
        # flexmock.MethodSignatureError:
        # edit(
        #    <copr.v3.proxies.project.ProjectProxy object at 0x7fa53af2f3d0>,
        #    ownername="the-owner",
        #    projectname="project-name",
        #    chroots=["fedora-rawhide-x86_64"],
        #    description="different description",
        #    instructions="the instructions",
        #    unlisted_on_hp=True,
        #    additional_repos=None,
        #    delete_after_days=60,
        # )
    ).and_return().once()

    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(config={"copr_url": "https://copr.fedorainfracloud.org"}),
    )

    build = flexmock(
        id="1",
        ownername=owner,
        projectname=project,
    )
    flexmock(BuildProxy).should_receive("create_from_file").and_return(build)
    build_id, url = api.run_copr_build(
        project=project,
        chroots=chroots,
        owner=owner,
        description="different description",
        instructions=instructions,
    )

    assert build_id == "1"
    assert url == f"https://copr.fedorainfracloud.org/coprs/build/{build.id}/"


def test_copr_build_existing_project_munch_no_settings_change(
    cwd_upstream_or_distgit,
    api_instance,
):
    u, d, api = api_instance
    owner = "the-owner"
    project = "project-name"
    chroots = ["fedora-rawhide-x86_64"]

    flexmock(ProjectProxy).should_receive("add").and_return(
        munchify(
            {
                "additional_repos": [],
                "auto_prune": True,
                "chroot_repos": {
                    "fedora-rawhide-x86_64": "https://download.copr.fedorainfracloud.org/"
                    "results/packit/packit-hello-world-127-stg/fedora-rawhide-x86_64/",
                },
                "contact": "https://github.com/packit/packit/issues",
                "description": "Continuous builds initiated by packit service.\n"
                "For more info check out https://packit.dev/",
                "devel_mode": False,
                "enable_net": False,
                "full_name": "packit/packit-hello-world-127-stg",
                "homepage": "",
                "id": 34245,
                "ownername": owner,
                "module_hotfixes": False,
            },
        ),
    )

    flexmock(ProjectProxy).should_receive("edit").and_return().times(0)

    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(config={"copr_url": "https://copr.fedorainfracloud.org"}),
    )

    build = flexmock(
        id="1",
        ownername=owner,
        projectname=project,
    )
    flexmock(BuildProxy).should_receive("create_from_file").and_return(build)
    build_id, url = api.run_copr_build(
        project=project,
        chroots=chroots,
        owner=owner,
        description=None,
        instructions=None,
        list_on_homepage=False,
        preserve_project=False,
        additional_repos=None,
    )

    assert build_id == "1"
    assert url == f"https://copr.fedorainfracloud.org/coprs/build/{build.id}/"


def test_copr_build_existing_project_munch_additional_repos_change(
    cwd_upstream_or_distgit,
    api_instance,
):
    u, d, api = api_instance
    owner = "the-owner"
    project = "project-name"
    chroots = ["fedora-rawhide-x86_64"]

    flexmock(ProjectProxy).should_receive("add").and_return(
        munchify(
            {
                "additional_repos": [],
                "auto_prune": True,
                "chroot_repos": {
                    "fedora-rawhide-x86_64": "https://download.copr.fedorainfracloud.org/"
                    "results/packit/packit-hello-world-127-stg/fedora-rawhide-x86_64/",
                },
                "contact": "https://github.com/packit/packit/issues",
                "description": "Continuous builds initiated by packit service.\n"
                "For more info check out https://packit.dev/",
                "devel_mode": False,
                "enable_net": False,
                "full_name": "packit/packit-hello-world-127-stg",
                "homepage": "",
                "id": 34245,
                "ownername": owner,
                "module_hotfixes": False,
            },
        ),
    )

    flexmock(ProjectProxy).should_receive("edit").and_return().once()

    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(config={"copr_url": "https://copr.fedorainfracloud.org"}),
    )

    build = flexmock(
        id="1",
        ownername=owner,
        projectname=project,
    )
    flexmock(BuildProxy).should_receive("create_from_file").and_return(build)
    build_id, url = api.run_copr_build(
        project=project,
        chroots=chroots,
        owner=owner,
        description=None,
        instructions=None,
        list_on_homepage=False,
        preserve_project=False,
        additional_repos=["new-repo"],
    )

    assert build_id == "1"
    assert url == f"https://copr.fedorainfracloud.org/coprs/build/{build.id}/"


def test_copr_build_existing_project_munch_list_on_homepage_change(
    cwd_upstream_or_distgit,
    api_instance,
):
    """
    We don't get that value from Copr. => We can't check the change. => No edit.
    """

    u, d, api = api_instance
    owner = "the-owner"
    project = "project-name"
    chroots = ["fedora-rawhide-x86_64"]

    flexmock(ProjectProxy).should_receive("add").and_return(
        munchify(
            {
                "additional_repos": [],
                "auto_prune": True,
                "chroot_repos": {
                    "fedora-rawhide-x86_64": "https://download.copr.fedorainfracloud.org/"
                    "results/packit/packit-hello-world-127-stg/fedora-rawhide-x86_64/",
                },
                "contact": "https://github.com/packit/packit/issues",
                "description": "Continuous builds initiated by packit service.\n"
                "For more info check out https://packit.dev/",
                "devel_mode": False,
                "enable_net": False,
                "full_name": "packit/packit-hello-world-127-stg",
                "homepage": "",
                "id": 34245,
                "ownername": owner,
                "module_hotfixes": False,
            },
        ),
    )

    # We don't get that value from Copr. => We can't check the change. => No edit.
    flexmock(ProjectProxy).should_receive("edit").and_return().times(0)

    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(config={"copr_url": "https://copr.fedorainfracloud.org"}),
    )

    build = flexmock(
        id="1",
        ownername=owner,
        projectname=project,
    )
    flexmock(BuildProxy).should_receive("create_from_file").and_return(build)
    build_id, url = api.run_copr_build(
        project=project,
        chroots=chroots,
        owner=owner,
        description=None,
        instructions=None,
        list_on_homepage=True,
        preserve_project=False,
        additional_repos=None,
    )

    assert build_id == "1"
    assert url == f"https://copr.fedorainfracloud.org/coprs/build/{build.id}/"


def test_copr_build_existing_project_munch_do_not_update_booleans_by_default(
    cwd_upstream_or_distgit,
    api_instance,
):
    u, d, api = api_instance
    owner = "the-owner"
    project = "project-name"
    chroots = ["fedora-rawhide-x86_64"]

    flexmock(ProjectProxy).should_receive("add").and_return(
        munchify(
            {
                "additional_repos": [],
                "auto_prune": True,
                "chroot_repos": {
                    "fedora-rawhide-x86_64": "https://download.copr.fedorainfracloud.org/"
                    "results/packit/packit-hello-world-127-stg/fedora-rawhide-x86_64/",
                },
                "contact": "https://github.com/packit-service/packit/issues",
                "description": "Continuous builds initiated by packit service.\n"
                "For more info check out https://packit.dev/",
                "unlisted_on_hp": True,  # Value not present currently.
                "devel_mode": False,
                "enable_net": False,
                "full_name": "packit/packit-hello-world-127-stg",
                "homepage": "",
                "id": 34245,
                "ownername": owner,
                "module_hotfixes": False,
            },
        ),
    )

    # Even if we receive this info from Copr, we can't edit that value if it is `None`.
    flexmock(ProjectProxy).should_receive("edit").and_return().times(0)

    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(config={"copr_url": "https://copr.fedorainfracloud.org"}),
    )

    build = flexmock(
        id="1",
        ownername=owner,
        projectname=project,
    )
    flexmock(BuildProxy).should_receive("create_from_file").and_return(build)
    build_id, url = api.run_copr_build(
        project=project,
        chroots=chroots,
        owner=owner,
        description=None,
        instructions=None,
        list_on_homepage=None,
        preserve_project=False,
        additional_repos=None,
    )

    assert build_id == "1"
    assert url == f"https://copr.fedorainfracloud.org/coprs/build/{build.id}/"


@pytest.mark.parametrize(
    "owner, requested_chroots, expected_chroots_for_edit",
    (
        # For Copr projects that are not created by Packit we try to extend the
        # chroots instead of replacing them.
        (
            "the-owner",
            ["fedora-rawhide-x86_64", "fedora-35-x86_64"],
            ["fedora-rawhide-x86_64", "fedora-35-x86_64", "epel-8-x86_64"],
        ),
        # For Copr projects that are not created by Packit we **do not** touch
        # chroots as long as the requirements for Copr build are satisfied.
        ("the-owner", ["fedora-rawhide-x86_64"], None),
    ),
)
def test_copr_build_existing_project_munch_chroot_updates(
    cwd_upstream_or_distgit,
    api_instance,
    owner,
    requested_chroots,
    expected_chroots_for_edit,
):
    u, d, api = api_instance
    project = "project-name"

    flexmock(ProjectProxy).should_receive("add").and_return(
        munchify(
            {
                "additional_repos": [],
                "auto_prune": True,
                "chroot_repos": {
                    "fedora-rawhide-x86_64": "https://download.copr.fedorainfracloud.org/"
                    "results/packit/packit-hello-world-127-stg/fedora-rawhide-x86_64/",
                    "epel-8-x86_64": "https://download.copr.fedorainfracloud.org/"
                    "results/packit/packit-hello-world-127-stg/epel-8-x86_64/",
                },
                "contact": "https://github.com/packit-service/packit/issues",
                "description": "Continuous builds initiated by packit service.\n"
                "For more info check out https://packit.dev/",
                "unlisted_on_hp": True,  # Value not present currently.
                "devel_mode": False,
                "enable_net": False,
                "full_name": "packit/packit-hello-world-127-stg",
                "homepage": "",
                "id": 34245,
                "ownername": owner,
                "module_hotfixes": False,
            },
        ),
    )

    if expected_chroots_for_edit:
        expected_chroots_for_edit.sort()
        flexmock(ProjectProxy).should_receive("edit").with_args(
            ownername=owner,
            projectname=project,
            chroots=expected_chroots_for_edit,
        ).and_return().once()
    else:
        flexmock(ProjectProxy).should_receive("edit").never()

    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(config={"copr_url": "https://copr.fedorainfracloud.org"}),
    )

    build = flexmock(
        id="1",
        ownername=owner,
        projectname=project,
    )
    flexmock(BuildProxy).should_receive("create_from_file").and_return(build)
    build_id, url = api.run_copr_build(
        project=project,
        chroots=requested_chroots,
        owner=owner,
        description=None,
        instructions=None,
        list_on_homepage=None,
        preserve_project=False,
        additional_repos=None,
    )

    assert build_id == "1"
    assert url == f"https://copr.fedorainfracloud.org/coprs/build/{build.id}/"


def test_copr_build_existing_project_error_on_change_settings(
    cwd_upstream_or_distgit,
    api_instance,
):
    u, d, api = api_instance
    owner = "the-owner"
    project = "project-name"
    description = "some description"
    instructions = "the instructions"
    chroots = ["fedora-rawhide-x86_64"]

    flexmock(ProjectProxy).should_receive("add").and_return(
        flexmock(
            chroot_repos=flexmock(keys=lambda: chroots),
            description=description,
            instructions=instructions,
            unlisted_on_hp=True,
            delete_after_days=60,
            additional_repos=[],
            ownername=owner,
            module_hotfixes=False,
        ),
    )

    flexmock(ProjectProxy).should_receive("request_permissions").with_args(
        ownername=owner,
        projectname=project,
        permissions={"admin": True},
    ).and_return()

    flexmock(ProjectProxy).should_receive("edit").and_raise(
        CoprAuthException,
        "Only owners and admins may update their projects.",
    ).once()

    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(config={"copr_url": "https://copr.fedorainfracloud.org"}),
    )

    build = flexmock(
        id="1",
        ownername=owner,
        projectname=project,
    )
    flexmock(BuildProxy).should_receive("create_from_file").and_return(build)

    with pytest.raises(PackitCoprSettingsException) as e_info:
        api.run_copr_build(
            project=project,
            chroots=chroots,
            owner=owner,
            description="different description",
            instructions=instructions,
        )
    assert e_info.value.fields_to_change == {
        "description": ("some description", "different description"),
    }


def test_copr_build_no_owner(cwd_upstream_or_distgit, api_instance):
    u, d, api = api_instance
    flexmock(CoprHelper).should_receive("get_copr_client").and_return(
        Client(config={"copr_url": "https://copr.fedorainfracloud.org"}),
    )
    with pytest.raises(PackitCoprException) as ex:
        api.run_copr_build(
            project="project-name",
            chroots="fedora-rawhide-x86_64",
            owner=None,
            description="some description",
            instructions="the instructions",
        )
    assert "owner not set" in str(ex)


def test_copr_build_cli_no_project_configured(upstream_and_remote, copr_client_mock):
    upstream, _ = upstream_and_remote
    flexmock(PackitAPI).should_receive("run_copr_build").with_args(
        project="packit-cli-upstream_remote-upstream_git-main",
        chroots=["fedora-rawhide-x86_64"],
        owner=None,
        description=None,
        instructions=None,
        upstream_ref=None,
        list_on_homepage=False,
        preserve_project=False,
        additional_repos=None,
        bootstrap=None,
        request_admin_if_needed=False,
        enable_net=False,
        release_suffix=None,
        srpm_path=None,
        module_hotfixes=False,
    ).and_return(("id", "url")).once()

    flexmock(packit.copr_helper.CoprClient).should_receive(
        "create_from_config_file",
    ).and_return(copr_client_mock)
    CoprHelper.get_available_chroots.cache_clear()

    run_packit(["build", "in-copr", "--no-wait"], working_dir=upstream)


def test_copr_build_cli_project_set_via_cli(upstream_and_remote, copr_client_mock):
    upstream, _ = upstream_and_remote
    flexmock(PackitAPI).should_receive("run_copr_build").with_args(
        project="the-project",
        chroots=["fedora-rawhide-x86_64"],
        owner=None,
        description=None,
        instructions=None,
        upstream_ref=None,
        list_on_homepage=False,
        preserve_project=False,
        additional_repos=None,
        bootstrap=None,
        request_admin_if_needed=False,
        enable_net=False,
        release_suffix=None,
        srpm_path=None,
        module_hotfixes=False,
    ).and_return(("id", "url")).once()

    flexmock(packit.copr_helper.CoprClient).should_receive(
        "create_from_config_file",
    ).and_return(copr_client_mock)
    CoprHelper.get_available_chroots.cache_clear()

    run_packit(
        ["build", "in-copr", "--no-wait", "--project", "the-project"],
        working_dir=upstream,
    )


def test_copr_build_cli_project_set_from_config(upstream_and_remote, copr_client_mock):
    upstream, _ = upstream_and_remote

    flexmock(PackageConfig).should_receive("get_copr_build_project_value").and_return(
        "some-project",
    )
    flexmock(packit.copr_helper.CoprClient).should_receive(
        "create_from_config_file",
    ).and_return(copr_client_mock)
    CoprHelper.get_available_chroots.cache_clear()

    flexmock(PackitAPI).should_receive("run_copr_build").with_args(
        project="some-project",
        chroots=["fedora-rawhide-x86_64"],
        owner=None,
        description=None,
        instructions=None,
        upstream_ref=None,
        list_on_homepage=False,
        preserve_project=False,
        additional_repos=None,
        bootstrap=None,
        request_admin_if_needed=False,
        enable_net=False,
        release_suffix=None,
        srpm_path=None,
        module_hotfixes=False,
    ).and_return(("id", "url")).once()

    run_packit(["build", "in-copr", "--no-wait"], working_dir=upstream)


def test_create_or_update_copr_project(copr_client_mock):
    copr_helper = CoprHelper(flexmock(git_url="https://gitlab.com/"))
    flexmock(packit.copr_helper.CoprClient).should_receive(
        "create_from_config_file",
    ).and_return(copr_client_mock)

    options = {
        "chroots": ["centos-stream-8-x86_64"],
        "description": "my fabulous test",
        "instructions": None,
        "owner": "me",
        "project": "already-present",
        "targets_dict": {"centos-stream-8": {"additional_packages": ["foo"]}},
        "module_hotfixes": None,
    }

    copr_client_mock.project_proxy = flexmock()
    copr_client_mock.project_chroot_proxy = flexmock()
    flexmock(copr_client_mock.project_proxy).should_receive("add").and_return(
        flexmock(
            chroot_repos={"centos-stream-8-x86_64": "https://repo.url"},
            **options,
        ),
    )
    flexmock(copr_client_mock.project_chroot_proxy).should_receive("get").and_return(
        {"additional_packages": []},
    )
    flexmock(copr_client_mock.project_chroot_proxy).should_receive("edit").with_args(
        ownername="me",
        projectname="already-present",
        chrootname="centos-stream-8-x86_64",
        additional_packages=["foo"],
    ).and_return({})

    copr_helper.create_or_update_copr_project(**options)


def test_create_or_update_copr_project_race_condition(copr_client_mock):
    copr_helper = CoprHelper(flexmock(git_url="https://gitlab.com/"))
    flexmock(packit.copr_helper.CoprClient).should_receive(
        "create_from_config_file",
    ).and_return(copr_client_mock)

    options = {
        "chroots": ["centos-stream-8-x86_64"],
        "description": "my fabulous test",
        "instructions": None,
        "owner": "me",
        "project": "already-present",
        "targets_dict": {"centos-stream-8": {"additional_packages": ["foo"]}},
        "module_hotfixes": None,
    }

    copr_client_mock.project_proxy = flexmock()
    copr_client_mock.project_chroot_proxy = flexmock()
    flexmock(copr_client_mock.project_proxy).should_receive("add").twice().and_raise(
        PackitCoprProjectException("already exists, 400 BAD REQUEST"),
    ).and_return(
        flexmock(
            chroot_repos={"centos-stream-8-x86_64": "https://repo.url"},
            **options,
        ),
    )
    flexmock(copr_client_mock.project_chroot_proxy).should_receive("get").and_return(
        {"additional_packages": []},
    )
    flexmock(copr_client_mock.project_chroot_proxy).should_receive("edit").with_args(
        ownername="me",
        projectname="already-present",
        chrootname="centos-stream-8-x86_64",
        additional_packages=["foo"],
    ).and_return({})

    copr_helper.create_or_update_copr_project(**options)


def test_create_or_update_copr_project_no_race_condition(copr_client_mock):
    copr_helper = CoprHelper(flexmock(git_url="https://gitlab.com/"))
    flexmock(packit.copr_helper.CoprClient).should_receive(
        "create_from_config_file",
    ).and_return(copr_client_mock)

    options = {
        "chroots": ["centos-stream-8-x86_64"],
        "description": "my fabulous test",
        "instructions": None,
        "owner": "me",
        "project": "already-present",
        "targets_dict": {"centos-stream-8": {"additional_packages": ["foo"]}},
        "module_hotfixes": None,
    }

    copr_client_mock.project_proxy = flexmock()
    copr_client_mock.project_chroot_proxy = flexmock()
    flexmock(copr_client_mock.project_proxy).should_receive("add").once().and_raise(
        PackitCoprProjectException("500 err"),
    )

    pytest.raises(
        PackitCoprProjectException,
        copr_helper.create_or_update_copr_project,
        **options,
    )
