import logging

import gitlab

from onegittorulethemall.services.abstract import GitService
from onegittorulethemall.utils import clone_repo_and_cd_inside, set_upstream_remote, \
    set_origin_remote, fetch_all

logger = logging.getLogger(__name__)


class GitlabService(GitService):
    name = "gitlab"

    def __init__(self, token=None, url=None, full_repo_name=None):
        super().__init__(token=token)
        url = url or "https://gitlab.com"
        self.g = gitlab.Gitlab(url=url, private_token=token)
        self.g.auth()
        self.user = self.g.users.list(username=self.g.user.username)[0]
        self.repo = None
        if full_repo_name:
            self.repo = self.g.projects.get(full_repo_name)

    @classmethod
    def create_from_remote_url(cls, remote_url, **kwargs):
        """ create instance of service from provided remote_url """
        raise NotImplementedError()

    @staticmethod
    def is_fork_of(user_repo, target_repo):
        """ is provided repo fork of the {parent_repo}/? """
        return user_repo.forked_from_project['id'] == target_repo.id

    def fork(self, target_repo):
        target_repo_org, target_repo_name = target_repo.split("/", 1)

        target_repo_gl = self.g.projects.get(target_repo)

        try:
            # is it already forked?
            user_repo = self.g.projects.get("{}/{}".format(self.user.username, target_repo_name))
            if not self.is_fork_of(user_repo, target_repo_gl):
                raise RuntimeError("repo %s is not a fork of %s" % (user_repo, target_repo_gl))
        except Exception:
            # nope
            user_repo = None

        if self.user.username == target_repo_org:
            # user wants to fork its own repo; let's just set up remotes 'n stuff
            if not user_repo:
                raise RuntimeError("repo %s not found" % target_repo_name)
            clone_repo_and_cd_inside(user_repo.path, user_repo.attributes['ssh_url_to_repo'],
                                     target_repo_org)
        else:
            user_repo = user_repo or self._fork_gracefully(target_repo_gl)

            clone_repo_and_cd_inside(user_repo.path, user_repo.attributes['ssh_url_to_repo'],
                                     target_repo_org)

            set_upstream_remote(clone_url=target_repo_gl.attributes['http_url_to_repo'],
                                ssh_url=target_repo_gl.attributes['ssh_url_to_repo'],
                                pull_merge_name="merge-requests")
        set_origin_remote(user_repo.attributes['ssh_url_to_repo'],
                          pull_merge_name="merge-requests")
        fetch_all()

    @staticmethod
    def _fork_gracefully(target_repo):
        """ fork if not forked, return forked repo """
        try:
            logger.info("forking repo %s", target_repo)
            fork = target_repo.forks.create({})
        except gitlab.GitlabCreateError as ex:
            logger.error("repo %s cannot be forked" % target_repo)
            raise RuntimeError("repo %s not found" % target_repo)

        return fork

    def create_pull_request(self, target_remote, target_branch, current_branch):
        raise NotImplementedError("Creating PRs for GitLab is not implemented yet.")

    def list_pull_requests(self):
        mrs = self.repo.mergerequests.list(state='opened',
                                           order_by='updated_at',
                                           sort='desc')
        return [
            {
                'id': mr.iid,
                'title': mr.title,
                'author': mr.author['username'],
                'url': mr.web_url,
            }
            for mr in mrs]

    def list_labels(self):
        """
        Get list of labels in the repository.
        :return: [Label]
        """
        return list(self.repo.labels.list())

    def update_labels(self, labels):
        """
        Update the labels of the repository. (No deletion, only add not existing ones.)

        :param labels: [str]
        :return: int - number of added labels
        """
        current_label_names = [l.name for l in list(self.repo.labels.list())]
        changes = 0
        for label in labels:
            if label.name not in current_label_names:
                color = self._normalize_label_color(color=label.color)
                self.repo.labels.create({'name': label.name,
                                         'color': color,
                                         'description': label.description or ""})

                changes += 1
        return changes

    @staticmethod
    def _normalize_label_color(color):
        if not color.startswith('#'):
            return '#{}'.format(color)
        return color
