"""
This bot will listen on fedmsg for finished CI runs and will update respective source gits


An example message:
{ 'crypto': 'x509',
  'headers': { },
  'i': 1,
  'msg': { 'CI_NAME': 'upstream-fedora-f28-pipeline',
           'CI_TYPE': 'custom',
           'branch': 'f28',
           'build_id': '335',
           'build_url': 'https://jenkins-continuous-infra...',
           'message-content': '',
           'namespace': 'rpms',
           'nvr': '',
           'original_spec_nvr': '',
           'ref': 'x86_64',
           'repo': 'gdb',
           'rev': '35cdcb6a32562b632c075f2fd42793f7492dcdb3',
           'status': 'SUCCESS',
           'test_guidance': "''",
           'topic': 'org.centos.prod.ci.pipeline.allpackages.complete',
           'username': 'jankratochvil'},
  'msg_id': '2018-1436f172-aa90-49f2-9ff0-9b34608f38e8',
  'source_name': 'datanommer',
  'source_version': '0.8.2',
  'timestamp': 1522055492.0,
  'topic': 'org.centos.prod.ci.pipeline.allpackages.complete',
  'username': None}

https://fedora-fedmsg.readthedocs.io/en/latest/topics.html#ci-pipeline-allpackages-complete


{ 'i': 3,
  'msg': { 'agent': 'pingou',
           'flag': { 'comment': 'Tests failed',
                     'date_created': '1433160759',
                     'percent': '0',
                     'pull_request_uid': 'cb0cc178203046fe86f675779b31b913',
                     'uid': 'jenkins_build_pagure_100+seed',
                     'url': 'http://jenkins.cloud.fedoraproject.org/',
                     'user': { 'default_email': 'bar@pingou.com',
                               'emails': [ 'bar@pingou.com',
                                           'foo@pingou.com'],
                               'fullname': 'PY C',
                               'name': 'pingou'},
                     'username': 'Jenkins'},
           'pullrequest': { 'assignee': None,
                            'branch': 'master',
                            'branch_from': 'master',
                            'comments': [],
                            'commit_start': None,
                            'commit_stop': None,
                            'date_created': '1433160759',
                            'id': 1,
                            'project': { 'date_created': '1433160759',
                                         'description': 'test project #1',
                                         'id': 1,
                                         'name': 'test',
                                         'parent': None,
                                         'settings': { 'Minimum_score_to_merge_pull-request': -1,
                                                       'Only_assignee_can_merge_pull-request': False,
                                                       'Web-hooks': None,
                                                       'issue_tracker': True,
                                                       'project_documentation': True,
                                                       'pull_requests': True},
                                         'user': { 'default_email': 'bar@pingou.com',
                                                   'emails': [ 'bar@pingou.com',
                                                               'foo@pingou.com'],
                                                   'fullname': 'PY C',
                                                   'name': 'pingou'}},
                            'repo_from': { 'date_created': '1433160759',
                                           'description': 'test project #1',
                                           'id': 1,
                                           'name': 'test',
                                           'parent': None,
                                           'settings': { 'Minimum_score_to_merge_pull-request': -1,
                                                         'Only_assignee_can_merge_pull-request': False,
                                                         'Web-hooks': None,
                                                         'issue_tracker': True,
                                                         'project_documentation': True,
                                                         'pull_requests': True},
                                           'user': { 'default_email': 'bar@pingou.com',
                                                     'emails': [ 'bar@pingou.com',
                                                                 'foo@pingou.com'],
                                                     'fullname': 'PY C',
                                                     'name': 'pingou'}},
                            'status': True,
                            'title': 'test pull-request',
                            'uid': 'cb0cc178203046fe86f675779b31b913',
                            'user': { 'default_email': 'bar@pingou.com',
                                      'emails': [ 'bar@pingou.com',
                                                  'foo@pingou.com'],
                                      'fullname': 'PY C',
                                      'name': 'pingou'}}},
  'msg_id': '2015-e7094e2a-1259-49da-91f5-635e81011ffa',
  'timestamp': 1433167960,
  'topic': 'io.pagure.prod.pagure.pull-request.flag.added',
  'username': 'pingou'}


Pull request info
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
import os
import re
import sys

import fedmsg
import libpagure
import github


package_mapping = {
    "python-docker": {
        "source-git": "https://github.com/TomasTomecek/docker-py-source-git"
    }
}


class Holyrood:
    """ such a good gin """

    def __init__(self):
        self.pagure_token = os.environ["PAGURE_API_TOKEN"]
        self.pagure = libpagure.Pagure(pagure_token=self.pagure_token)
        self.g = github.Github()

    def process_pr(self, msg):
        """
        Process flags from the PR and update source git PR with those flags
        :param msg:
        :return:
        """
        try:
            source_git = package_mapping[msg["msg"]["pullrequest"]["project"]["name"]]
        except KeyError:
            print("invalid message format or source git not found")
            return
        pr_id = msg["msg"]["pullrequest"]["id"]
        pr_info = self.pagure.request_info(pr_id)
        pr_description = pr_info["comments"][0]

        # find info for the matching source git pr
        re_search = re.search(r"Source-git pull request ID: (\d+)", pr_description)
        try:
            sg_pr_id = int(re_search[0])
        except (IndexError, ValueError):
            print("Source git PR not found")
            return

        repo = self.g.get_repo(source_git)
        sg_pull = repo.get_pull(sg_pr_id)
        top_commit = sg_pull.get_commits()[-1]  # or [0]
        top_commit.create_status(...)


def main():
    """
    watch for flags on PRs: try to process those which we know mapping for

    :return: int, retcode
    """
    # we can watch for runs directly:
    # "org.centos.prod.ci.pipeline.allpackages.complete"
    topic = "io.pagure.prod.pagure.pull-request.flag.added"

    h = Holyrood()

    for name, endpoint, topic, msg in fedmsg.tail_messages(topic=topic):
        h.process_pr(msg)
    return 0


if __name__ == '__main__':
    sys.exit(main())
