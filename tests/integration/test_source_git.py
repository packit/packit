# Copyright (c) 2019 Red Hat, Inc.

from packit.utils.commands import cwd
    create_git_am_style_history,
        directory=sourcegit,
        message="source change\nignore: true",
    mock_spec_download_remote_s(sg_path, sg_path / "fedora", "0.1.0")
    mock_spec_download_remote_s(sg_path, sg_path / "fedora", "0.1.0")


def test_srpm_git_am(mock_remote_functionality_sourcegit, api_instance_source_git):
    sg_path = Path(api_instance_source_git.upstream_local_project.working_dir)
    mock_spec_download_remote_s(sg_path, sg_path / "fedora", "0.1.0")

    api_instance_source_git.up.specfile.spec_content.section("%package")[10:10] = (
        "Patch1: citra.patch",
        "Patch2: malt.patch",
        "Patch8: 0001-m04r-malt.patch",
    )
    autosetup_line = api_instance_source_git.up.specfile.spec_content.section("%prep")[
        0
    ]
    autosetup_line = autosetup_line.replace("-S patch", "-S git_am")
    api_instance_source_git.up.specfile.spec_content.section("%prep")[
        0
    ] = autosetup_line
    api_instance_source_git.up.specfile.save()

    create_git_am_style_history(sg_path)

    with cwd(sg_path):
        api_instance_source_git.create_srpm(upstream_ref="0.1.0")

    srpm_path = list(sg_path.glob("beer-0.1.0-2.*.src.rpm"))[0]
    assert srpm_path.is_file()
    build_srpm(srpm_path)

    assert set([x.name for x in sg_path.joinpath("fedora").glob("*.patch")]) == {
        "citra.patch",
        "0001-m04r-malt.patch",
        "malt.patch",
    }