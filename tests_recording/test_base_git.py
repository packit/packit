# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
from pathlib import Path

from flexmock import flexmock
from requre.cassette import DataTypes
from requre.online_replacing import (
    record_requests_for_all_methods,
)

from packit.base_git import PackitRepositoryBase
from packit.config import PackageConfig
from packit.config.sources import SourcesItem
from packit.specfile import Specfile
from tests_recording.testbase import PackitTest


@record_requests_for_all_methods()
class ProposeUpdate(PackitTest):
    def cassette_setup(self, cassette):
        cassette.data_miner.data_type = DataTypes.Dict

    def test_download_remote_sources_via_spec(self):
        """
        Use case: package_config.sources and Source0 are out of sync,
        make sure packit downloads correct archive specifiec in the spec file
        """
        # we should use an actual git.centos.org url but we'd store the tarball in our history
        # which we don't want I'd say
        # "https://git.centos.org/sources/rsync/c8s/82e7829c0b3cefbd33c233005341e2073c425629"
        git_centos_org_url = "https://example.org/"
        package_config = PackageConfig(
            specfile_path="rsync.spec",
            sources=[
                SourcesItem(
                    path="rsync-3.1.2.tar.gz",
                    url=git_centos_org_url,
                ),
            ],
            jobs=[],
        )
        # same drill here, let's not store tarballs in our git-history
        # source = "https://download.samba.org/pub/rsync/src/rsync-3.1.3.tar.gz"
        source = "https://httpbin.org/anything/rsync-3.1.3.tar.gz"

        base_git = PackitRepositoryBase(
            config=flexmock(), package_config=package_config
        )
        specfile_content = (
            "Name: rsync\n"
            "Version: 3.1.3\n"
            "Release: 1\n"
            f"Source0: {source}\n"
            "License: GPLv3+\n"
            "Summary: rsync\n"
            "%description\nrsync\n"
        )
        tmp = Path(self.static_tmp)
        spec_path = tmp / "rsync.spec"
        spec_path.write_text(specfile_content)
        specfile = Specfile(spec_path, sources_dir=tmp)
        flexmock(base_git).should_receive("specfile").and_return(specfile)

        flexmock(Path).should_receive("is_file").and_return(False)

        base_git.download_remote_sources()

        expected_path = tmp / "rsync-3.1.3.tar.gz"
        assert Path(expected_path).exists()
