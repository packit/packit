class GitService:
    def __init__(self, token=None):
        self.token = token

    @classmethod
    def create_from_remote_url(cls, remote_url):
        """ create instance of service from provided remote_url """
        raise NotImplementedError()

    def create_fork(self, target_repo):
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

    def branches(self):
        raise NotImplementedError()

    def get_fork(self):
        raise NotImplementedError()

