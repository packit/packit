import libpagure

from onegittorulethemall.services.abstract import GitService


class PagureService(GitService):
    def __init__(
            self,
            token=None,
            full_repo_name=None,
            instance_url="https://src.fedoraproject.org/",
            **kwargs,
    ):
        super().__init__(token)
        self.pagure = OurPagure(
            pagure_token=token,
            pagure_repository=full_repo_name,
            instance_url=instance_url,
            **kwargs,
        )

    def pr_list(self):
        self.pagure.list_requests()

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
        return self.pagure.create_request(title=title,
                                          body=body,
                                          target_branch=target_branch,
                                          source_branch=source_branch)

    def create_fork(self, target_repo, namespace=None):
        return self.pagure.new_project(
            name=self.pagure.repo,
            description=None,
            namespace=namespace
        )


class OurPagure(libpagure.Pagure):

    def create_request(self, title, body, target_branch, source_branch):
        request_url = f"{self.instance}/api/0/fork/" \
                      f"{self.username}/{self.repo}/pull-request/new"

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

        request_url = f"{self.instance}/api/0/fork/" \
                      f"{self.username}/{self.namespace}/{self.repo}/git/urls"

        try:
            return_value = self._call_api(
                url=request_url,
                method="GET",
                data={},
            )
            return return_value
        except:
            return None
