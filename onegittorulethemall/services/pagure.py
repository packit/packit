import logging
from functools import lru_cache

import libpagure

from onegittorulethemall.services.abstract import GitService, GitProject

logger = logging.getLogger(__name__)


class PagureService(GitService):
    def __init__(
            self, token=None, instance_url="https://src.fedoraproject.org", **kwargs
    ):
        super().__init__()
        self.instance_url = instance_url
        self.token = token
        self.pagure_kwargs = kwargs

        self.pagure = OurPagure(pagure_token=token, instance_url=instance_url, **kwargs)

    def get_project(self, **kwargs):
        project_kwargs = self.pagure_kwargs.copy()
        project_kwargs.update(kwargs)
        return PagureProject(
            instance_url=self.instance_url, token=self.token, **project_kwargs
        )


class OurPagure(libpagure.Pagure):
    """TODO: Move this functionality to upstream libpagure"""

    def __init__(self, namespace=None, **kwargs):
        super().__init__(**kwargs)
        self.namespace = namespace

    @property
    def api_url(self):
        return f"{self.instance}/api/0/"

    @property
    def repo_name(self):
        return self.repo.split("/")[1]

    def get_api_url(self, *args):
        args_list = []

        if self.username:
            args_list += ["fork", self.username]

        args_list += filter(lambda x: x is not None, args)

        return self.api_url + "/".join(args_list)

    def create_request(self, title, body, target_branch, source_branch):
        """
        PAGURE DOCS:

        Create pull-request
        -------------------
        Open a new pull-request from this project to itself or its parent (if
        this project is a fork).

        ::

            POST /api/0/<repo>/pull-request/new
            POST /api/0/<namespace>/<repo>/pull-request/new

        ::

            POST /api/0/fork/<username>/<repo>/pull-request/new
            POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/new

        Input
        ^^^^^

        +--------------------+----------+---------------+----------------------+
        | Key                | Type     | Optionality   | Description          |
        +====================+==========+===============+======================+
        | ``title``          | string   | Mandatory     | The title to give to |
        |                    |          |               | this pull-request    |
        +--------------------+----------+---------------+----------------------+
        | ``branch_to``      | string   | Mandatory     | The name of the      |
        |                    |          |               | branch the submitted |
        |                    |          |               | changes should be    |
        |                    |          |               | merged into.         |
        +--------------------+----------+---------------+----------------------+
        | ``branch_from``    | string   | Mandatory     | The name of the      |
        |                    |          |               | branch containing    |
        |                    |          |               | the changes to merge |
        +--------------------+----------+---------------+----------------------+
        | ``initial_comment``| string   | Optional      | The intial comment   |
        |                    |          |               | describing what these|
        |                    |          |               | changes are about.   |
        +--------------------+----------+---------------+----------------------+

        Sample response
        ^^^^^^^^^^^^^^^

        ::

            {
              "assignee": null,
              "branch": "master",
              "branch_from": "master",
              "closed_at": null,
              "closed_by": null,
              "comments": [],
              "commit_start": null,
              "commit_stop": null,
              "date_created": "1431414800",
              "id": 1,
              "project": {
                "close_status": [],
                "custom_keys": [],
                "date_created": "1431414800",
                "description": "test project #1",
                "id": 1,
                "name": "test",
                "parent": null,
                "user": {
                  "fullname": "PY C",
                  "name": "pingou"
                }
              },

              "repo_from": {
                "date_created": "1431414800",
                "description": "test project #1",
                "id": 1,
                "name": "test",
                "parent": null,
                "user": {
                  "fullname": "PY C",
                  "name": "pingou"
                }
              },
              "status": "Open",
              "title": "test pull-request",
              "uid": "1431414800",
              "updated_on": "1431414800",
              "user": {
                "fullname": "PY C",
                "name": "pingou"
              }
            }
        """
        request_url = self.get_api_url(
            "fork", self.username, self.namespace, self.repo, "pull-request", "new"
        )

        return_value = self._call_api(
            url=request_url,
            method="POST",
            data={
                "title": title,
                "branch_to": target_branch,
                "branch_from": source_branch,
                "initial_comment": body,
            },
        )
        return return_value["id"]

    def get_fork(self):

        request_url = self.get_api_url(self.repo)

        try:
            return_value = self._call_api(url=request_url, method="GET", data={})
            return return_value
        except Exception as ex:
            return None

    def create_fork(self):
        """
        PAGURE DOCS:

        Fork a project

        --------------------

        Fork a project on this pagure instance.
        This is an asynchronous call.

        ::

        POST /api/0/fork

        Input

        ^^^^^

        +------------------+---------+--------------+---------------------------+
        | Key              | Type    | Optionality  | Description               |
        +==================+=========+==============+===========================+
        | ``repo``         | string  | Mandatory    | | The name of the project |
        |                  |         |              |   to fork.                |
        +------------------+---------+--------------+---------------------------+
        | ``namespace``    | string  | Optional     | | The namespace of the    |
        |                  |         |              |   project to fork.        |
        +------------------+---------+--------------+---------------------------+
        | ``username``     | string  | Optional     | | The username of the user|
        |                  |         |              |   of the fork.            |
        +------------------+---------+--------------+---------------------------+
        | ``wait``         | boolean | Optional     | | A boolean to specify if |
        |                  |         |              |   this API call should    |
        |                  |         |              |   return a taskid or if it|
        |                  |         |              |   should wait for the task|
        |                  |         |              |   to finish.              |
        +------------------+---------+--------------+---------------------------+

        Sample response

        ^^^^^^^^^^^^^^^

        ::

        wait=False:

        {
          "message": "Project forking queued",
          "taskid": "123-abcd"
        }



        wait=True:

        {
          "message": 'Repo "test" cloned to "pingou/test"
        }


        """
        request_url = self.get_api_url("fork")

        return_value = self._call_api(
            url=request_url,
            method="POST",
            data={"repo": self.repo_name, "namespace": self.namespace, "wait": True},
        )
        return return_value

    @property
    def project_exists(self):
        request_url = self.get_api_url(self.repo)
        try:
            self._call_api(url=request_url, method="GET", data={})
            return True
        except:
            return False

    @property
    @lru_cache()
    def project_info(self):
        request_url = self.get_api_url(self.repo)

        return_value = self._call_api(url=request_url, method="GET", data={})
        return return_value

    @property
    def project_description(self):
        return self.project_info["description"]

    @property
    def parent(self):
        return self.project_info["parent"]

    @property
    def git_urls(self):
        request_url = self.get_api_url(self.repo, "git", "urls")

        return_value = self._call_api(url=request_url, method="GET", data={})
        return return_value["urls"]

    @property
    def branches(self):
        request_url = self.get_api_url(self.repo, "git", "branches")

        return_value = self._call_api(url=request_url, method="GET", data={})
        return return_value["branches"]

    def get_commit_flags(self, commit):
        request_url = self.get_api_url(self.repo, "c", commit, "flag")

        return_value = self._call_api(url=request_url, method="GET", data={})
        return return_value["flags"]


class PagureProject(GitProject):
    def __init__(
            self,
            repo=None,
            namespace=None,
            username=None,
            instance_url=None,
            token=None,
            is_fork=False,
            **kwargs,
    ):
        super().__init__()
        self.repo = repo
        self.namespace = namespace
        self.username = username
        self.instance_url = instance_url
        self.token = token
        self._is_fork = is_fork or False
        self.pagure_kwargs = kwargs

        self.pagure = OurPagure(
            pagure_token=token,
            pagure_repository=f"{self.namespace}/{self.repo}",
            namespace=namespace,
            fork_username=username if is_fork else None,
            instance_url=instance_url,
            **kwargs,
        )

    @property
    def branches(self):
        return self.pagure.branches

    @property
    def description(self):
        return self.pagure.project_description

    def pr_list(self, status="open"):
        return self.pagure.list_requests(status=status)

    def pr_comment(self, pr_id, body, commit=None, filename=None, row=None):
        return self.pagure.comment_request(
            request_id=pr_id, body=body, commit=commit, filename=filename, row=row
        )

    def pr_close(self, pr_id):
        return self.pagure.close_request(request_id=pr_id)

    def pr_info(self, pr_id):
        return self.pagure.request_info(request_id=pr_id)

    def pr_merge(self, pr_id):
        return self.pagure.merge_request(request_id=pr_id)

    def pr_create(self, title, body, target_project, target_branch, source_branch):
        return self.pagure.create_request(
            title=title,
            body=body,
            target_branch=target_branch,
            source_branch=source_branch,
        )

    def fork_create(self):
        return self.pagure.create_fork()

    @property
    def fork(self):
        """PagureRepo instance of the fork of this repo."""
        kwargs = self.pagure_kwargs
        kwargs.update(
            repo=self.repo,
            namespace=self.namespace,
            username=self.username,
            instance_url=self.instance_url,
            token=self.token,
            is_fork=True,
        )
        fork_project = PagureProject(**kwargs)
        try:
            if fork_project.exists and fork_project.pagure.parent:
                return fork_project
        except:
            return None
        return None

    @property
    def is_fork(self):
        return self._is_fork

    @property
    def exists(self):
        return self.pagure.project_exists

    @property
    def is_forked(self):
        return self.fork is not None

    @property
    def git_urls(self):
        return self.pagure.git_urls

    def get_commit_flags(self, commit):
        return self.pagure.get_commit_flags(commit=commit)
