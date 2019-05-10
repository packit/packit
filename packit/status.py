# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging

from typing import List, Tuple, Dict

from ogr.abstract import Release

from packit.config import Config, PackageConfig
from packit.distgit import DistGit
from packit.exceptions import PackitException
from packit.upstream import Upstream

logger = logging.getLogger(__name__)


class Status:
    """
    This class provides methods to obtain status of the package
    """

    def __init__(
        self,
        config: Config,
        package_config: PackageConfig,
        upstream: Upstream,
        distgit: DistGit,
    ):
        self.config = config
        self.package_config = package_config

        self.up = upstream
        self.dg = distgit

    def get_downstream_prs(self, number_of_prs: int = 5) -> List[Tuple[int, str, str]]:
        """
        Get specific number of latest downstream PRs
        :param number_of_prs: int
        :return: List of downstream PRs
        """
        table: List[Tuple[int, str, str]] = []
        pr_list = self.dg.local_project.git_project.get_pr_list()
        logger.debug("Downstream PRs fetched.")
        if len(pr_list) > 0:
            # take last `number_of_prs` PRs
            pr_list = (
                pr_list[:number_of_prs] if len(pr_list) > number_of_prs else pr_list
            )
            table = [(pr.id, pr.title, pr.url) for pr in pr_list]
        return table

    def get_dg_versions(self) -> Dict:
        """
        Get versions from all branches in Dist-git
        :return: Dict {"branch": "version"}
        """
        dg_versions = {}
        branches = self.dg.local_project.git_project.get_branches()
        logger.debug("Dist-git branches fetched.")
        for branch in branches:
            try:
                self.dg.create_branch(
                    branch, base=f"remotes/origin/{branch}", setup_tracking=False
                )
                self.dg.checkout_branch(branch)
            except Exception as ex:
                logger.debug(f"Branch {branch} is not present: {ex}")
                continue
            try:
                dg_versions[branch] = self.dg.specfile.get_version()
            except PackitException:
                logger.debug(f"Can't figure out the version of branch: {branch}")
        self.dg.checkout_branch("master")

        return dg_versions

    def get_up_releases(self, number_of_releases: int = 5) -> List:
        """
        Get specific number of latest upstream releases
        :param number_of_releases: int
        :return: List
        """
        if not self.up.local_project.git_project:
            logger.info("We couldn't track any upstream releases.")
            return []

        latest_releases: List[Release] = []
        try:
            latest_releases = self.up.local_project.git_project.get_releases()
            logger.debug("Upstream releases fetched.")
        except PackitException as e:
            logger.debug("Failed to fetch upstream releases: %s", e)

        return latest_releases[:number_of_releases]

    def get_builds(self,) -> Dict:
        """
        Get latest koji builds
        """
        # https://github.com/fedora-infra/bodhi/issues/3058
        from bodhi.client.bindings import BodhiClient

        b = BodhiClient()
        # { koji-target: "latest-build-nvr"}
        builds_d = b.latest_builds(self.dg.package_name)
        branches = self.dg.local_project.git_project.get_branches()
        logger.debug("Latest koji builds fetched.")
        builds: Dict = {}
        for branch in branches:
            # there is no master tag in koji
            if branch == "master":
                continue
            koji_tag = f"{branch}-updates-candidate"
            try:
                builds[branch] = builds_d[koji_tag]
            except KeyError:
                logger.info(f"There are no builds for branch {branch}")
        return builds

    def get_updates(self, number_of_updates: int = 3) -> List:
        """
        Get specific number of latest updates in bodhi
        :param number_of_updates: int
        :return: None
        """
        # https://github.com/fedora-infra/bodhi/issues/3058
        from bodhi.client.bindings import BodhiClient

        b = BodhiClient()
        results = b.query(packages=self.dg.package_name)["updates"]
        logger.debug("Bodhi updates fetched.")
        results = results[:number_of_updates]

        return [
            [result["title"], result["karma"], result["status"]] for result in results
        ]
