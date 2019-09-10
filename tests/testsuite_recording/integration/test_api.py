import os
from packit.api import PackitAPI
from subprocess import check_output
from flexmock import flexmock
from tests.testsuite_recording.integration.testbase import PackitUnittestOgr


class ProposeUpdate(PackitUnittestOgr):
    def setUp(self):
        super().setUp()
        self.api = PackitAPI(
            config=self.conf, package_config=self.pc, upstream_local_project=self.lp
        )
        self.api._up = self.upstream
        self.api._dg = self.dg
        # Do not upload package, because no credentials given in CI
        flexmock(self.api).should_receive("_handle_sources").and_return(None)
        flexmock(self.api.dg).should_receive("push_to_fork").and_return(None)
        self.set_git_user()

    def test_propose_update(self):
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
