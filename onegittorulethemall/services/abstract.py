class GitService:
    def __init__(self):
        pass

    @classmethod
    def create_from_remote_url(cls, remote_url):
        """ create instance of service from provided remote_url """
        raise NotImplementedError()

    def get_project(self, namespace=None, user=None, repo=None):
        raise NotImplementedError


class GitProject:

    @property
    def branches(self):
        raise NotImplementedError()

    @property
    def description(self):
        raise NotImplementedError()

    def pr_create(self, title, body, target_project, target_branch, current_branch):
        raise NotImplementedError()

    def pr_list(self):
        raise NotImplementedError()

    def pr_comment(self, pr_id, body, commit=None, filename=None, row=None):
        raise NotImplementedError()

    def pr_close(self, pr_id):
        raise NotImplementedError()

    def pr_info(self, pr_id):
        raise NotImplementedError()

    def pr_merge(self, pr_id):
        raise NotImplementedError()

    @property
    def fork(self):
        raise NotImplementedError()

    @property
    def is_forked(self):
        raise NotImplementedError()

    def fork_create(self):
        raise NotImplementedError()
