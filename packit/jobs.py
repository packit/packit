"""
We love you, Steve Jobs.
"""
import logging
from typing import List, Optional, Tuple, Dict, Type

from ogr.abstract import GitProject
from ogr.services.github import GithubProject, GithubService

from packit.api import PackitAPI
from packit.config import JobConfig, JobTriggerType, JobType, PackageConfig, Config
from packit.config import get_packit_config_from_repo
from packit.local_project import LocalProject
from packit.utils import nested_get

logger = logging.getLogger(__name__)


JOB_NAME_HANDLER_MAPPING: Dict[JobType, Type["JobHandler"]] = {}


def add_to_mapping(kls: Type["JobHandler"]):
    JOB_NAME_HANDLER_MAPPING[kls.name] = kls
    return kls


class SteveJobs:
    """
    Steve makes sure all the jobs are done with precision.
    """

    def __init__(self, config: Config):
        self.config = config
        self._github_service = None

    @property
    def github_service(self):
        if self._github_service is None:
            self._github_service = GithubService(token=self.config.github_token)
        return self._github_service

    def get_package_config_from_github_release(
        self, event: dict
    ) -> Optional[Tuple[JobTriggerType, PackageConfig, GitProject]]:
        """ look into the provided event and see if it's one for a published github release """
        action = nested_get(event, "action")
        logger.debug(f"action = {action}")
        release = nested_get(event, "release")
        if action == "published" and release:
            repo_namespace = nested_get(event, "repository", "owner", "login")
            repo_name = nested_get(event, "repository", "name")
            if not (repo_namespace and repo_name):
                logger.warning(
                    "We could not figure out the full name of the repository."
                )
                return None
            release_ref = nested_get(event, "release", "tag_name")
            if not release_ref:
                logger.warning("Release tag name is not set.")
                return None
            logger.info(
                f"New release event {release_ref} for repo {repo_namespace}/{repo_name}."
            )
            gh_proj = GithubProject(
                repo=repo_name, namespace=repo_namespace, service=self.github_service
            )
            package_config = get_packit_config_from_repo(gh_proj, release_ref)
            https_url = event["repository"]["html_url"]
            package_config.upstream_project_url = https_url
            return JobTriggerType.release, package_config, gh_proj
        return None

    def get_package_config_from_github_pr(
        self, event: dict
    ) -> Optional[Tuple[JobTriggerType, PackageConfig, GitProject]]:
        """ look into the provided event and see if it's one for a published github release """
        action = nested_get(event, "action")
        logger.debug(f"action = {action}")
        pr_id = nested_get(event, "number")
        if action in ["opened", "reopened", "synchronize"] and pr_id:
            repo_namespace = nested_get(
                event, "pull_request", "head", "repo", "owner", "login"
            )
            repo_name = nested_get(event, "pull_request", "head", "repo", "name")
            if not (repo_namespace and repo_name):
                logger.warning(
                    "We could not figure out the full name of the repository."
                )
                return None
            ref = nested_get(event, "pull_request", "head", "ref")
            if not ref:
                logger.warning("Ref where the PR is coming from is not set.")
                return None
            target_repo = nested_get(event, "repository", "full_name")
            logger.info(f"GitHub pull request {pr_id} event for repo {target_repo}.")
            gh_proj = GithubProject(
                repo=repo_name, namespace=repo_namespace, service=self.github_service
            )
            package_config = get_packit_config_from_repo(gh_proj, ref)
            https_url = event["repository"]["html_url"]
            package_config.upstream_project_url = https_url
            return JobTriggerType.pull_request, package_config, gh_proj
        return None

    def parse_event(
        self, event: dict
    ) -> Optional[Tuple[JobTriggerType, PackageConfig, GitProject]]:
        """
        When a new event arrives, we need to figure out if we are able to process it.

        :param event: webhook payload or fedmsg
        """
        if event:
            # Once we'll start processing multiple events from different sources,
            # we should probably break this method down and move it to handlers or JobTrigger

            # github webhooks
            respone = self.get_package_config_from_github_release(event)
            if respone:
                return respone
            # TODO: pull requests
        return None

    def process_jobs(
        self,
        trigger: JobTriggerType,
        package_config: PackageConfig,
        event: dict,
        project: GitProject,
    ):
        for job in package_config.jobs:
            if trigger == job.trigger:
                handler_kls = JOB_NAME_HANDLER_MAPPING.get(job.job, None)
                if not handler_kls:
                    logger.warning(f"There is no handler for job {job}")
                    continue
                handler = handler_kls(self.config, package_config, event, project, job)
                handler.run()

    def process_message(self, event: dict):
        """ this is the entrypoint """
        response = self.parse_event(event)
        if not response:
            logger.debug("We don't process this event")
            return
        trigger, package_config, project = response
        if not all([trigger, package_config, project]):
            logger.debug("This project is not using packit.")
            return
        self.process_jobs(trigger, package_config, event, project)


class JobHandler:
    """ Generic interface to handle different type of inputs """

    name: JobType
    triggers: List[JobTriggerType]

    def __init__(
        self,
        config: Config,
        package_config: PackageConfig,
        event: dict,
        project: GitProject,
        job: JobConfig,
    ):
        self.config: Config = config
        self.project: GitProject = project
        self.package_config: PackageConfig = package_config
        self.event: dict = event
        self.job: JobConfig = job

    def run(self):
        raise NotImplementedError("This should have been implemented.")


class FedmsgHandler(JobHandler):
    """ Handlers for events from fedmsg """

    topic: str


# class NewDistGitPRFlag(FedmsgHandler):
#     """ A new flag was added to a dist-git pull request """
#     topic = "org.fedoraproject.prod.pagure.pull-request.flag.added"
#     name = "?"
#
#     def run(self):
#         repo_name = self.event["msg"]["pull_request"]["project"]["name"]
#         namespace = self.event["msg"]["pull_request"]["project"]["namespace"]
#         pr_id = self.event["msg"]["pull_request"]["id"]
#
#         pull_request = pagure_repo.get_pr_info(pr_id=pr_id)


@add_to_mapping
class GithubPullRequestHandler(JobHandler):
    name = JobType.check_downstream
    triggers = [JobTriggerType.pull_request]
    # https://developer.github.com/v3/activity/events/types/#events-api-payload-28

    def run(self):
        pr_id = self.event["pull_request"]["number"]

        local_project = LocalProject(git_project=self.project)

        api = PackitAPI(self.config, self.package_config, local_project)

        api.sync_pr(
            pr_id=pr_id,
            dist_git_branch=self.job.metadata.get("dist-git-branch", "master"),
            # TODO: figure out top upstream commit for source-git here
        )


@add_to_mapping
class GithubReleaseHandler(JobHandler):
    name = JobType.propose_downstream
    triggers = [JobTriggerType.release]

    def run(self):
        """
        Sync the upstream release to dist-git as a pull request.
        """
        version = self.event["release"]["tag_name"]

        local_project = LocalProject(git_project=self.project)

        api = PackitAPI(self.config, self.package_config, local_project)

        api.sync_release(
            dist_git_branch=self.job.metadata.get("dist-git-branch", "master"),
            version=version,
        )
