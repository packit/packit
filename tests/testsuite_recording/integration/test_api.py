"""
Tests of packit APIs
to generate all tests, please run it twice with different ogr versions
until ogr will not have _feature_id in rpm or pypi
"""

import importlib
import inspect
import os
import unittest
from subprocess import check_output

from flexmock import flexmock
from rebasehelper.exceptions import RebaseHelperError

from packit.api import PackitAPI
from tests.testsuite_recording.integration.testbase import PackitUnittestOgr


class ProposeUpdate(PackitUnittestOgr):
    @classmethod
    def _feature_id(cls):
        ogr_module = importlib.import_module("ogr")
        if "parent" in inspect.getsource(
            ogr_module.services.pagure.PagureProject.is_fork.fget
        ):
            cls.variant = "ogr_old_fork"

    def setUp(self):
        self._feature_id()
        super().setUp()
        self.api = PackitAPI(
            config=self.conf, package_config=self.pc, upstream_local_project=self.lp
        )
        self.api._up = self.upstream
        self.api._dg = self.dg
        self.set_git_user()

    def check_version_increase(self):
        # change specfile little bit to have there some change
        specfile_location = os.path.join(self.lp.working_dir, "python-ogr.spec")
        with open(specfile_location, "r") as myfile:
            filedata = myfile.read()
        # Patch the specfile with new version
        version_increase = "0.0.0"
        for line in filedata.splitlines():
            if "Version:" in line:
                version = line.rsplit(" ", 1)[1]
                v1, v2, v3 = version.split(".")
                version_increase = ".".join([v1, str(int(v2) + 1), v3])
                filedata = filedata.replace(version, version_increase)
                break
        with open(specfile_location, "w") as myfile:
            myfile.write(filedata)
        check_output(
            f"cd {self.lp.working_dir};"
            f"git commit -m 'test change' python-ogr.spec;"
            f"git tag -a {version_increase} -m 'my version {version_increase}'",
            shell=True,
        )
        self.api.sync_release("master")

    @unittest.skip(
        reason="https://github.com/packit-service/packit/issues/562 and #561"
    )
    def test_comment_in_spec(self):
        """
        change specfile little bit to have there some change, do not increase version
        """
        specfile_location = os.path.join(self.lp.working_dir, "python-ogr.spec")
        version_increase = "10.0.0"
        with open(specfile_location, "a") as myfile:
            myfile.write("\n# comment\n")
        check_output(
            f"cd {self.lp.working_dir};"
            f"git commit -m 'test change' python-ogr.spec;"
            f"git tag -a {version_increase} -m 'my version {version_increase}'",
            shell=True,
        )
        self.api.sync_release("master")

    # @unittest.skipIf(
    #     hasattr(rebasehelper, "VERSION")
    #     and int(rebasehelper.VERSION.split(".")[1]) >= 19,
    #     "Older version of rebasehelper raised exception",
    # )
    @unittest.skip(
        reason="https://github.com/packit-service/packit/issues/562 and #561"
    )
    def test_version_change_exception(self):
        """
        check if it raises exception, because sources are not uploaded in distgit
        Downgrade rebasehelper to version < 0.19.0
        """
        self.assertRaises(RebaseHelperError, self.check_version_increase)

    # @unittest.skipUnless(
    #     hasattr(rebasehelper, "VERSION")
    #     and int(rebasehelper.VERSION.split(".")[1]) >= 19,
    #     "New version of rebasehelper works without raised exception",
    # )
    @unittest.skip(reason="https://github.com/packit-service/packit/issues/558")
    def test_version_change_new_rebaseheler(self):
        """
        check if it not raises exception, because sources are not uploaded in distgit
        """
        self.check_version_increase()

    @unittest.skip(
        reason="https://github.com/packit-service/packit/issues/562 and #561"
    )
    def test_version_change_mocked(self):
        """
        version is not not uploaded, so skip in this test
        """
        flexmock(self.api).should_receive("_handle_sources").and_return(None)
        self.check_version_increase()
