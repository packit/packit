# `packit sync-from-downstream`

This is a detailed documentation for the downstream sync functionality of packit. The
command creates a new pull request in upstream repository using a
selected branch (master by default) from Fedora dist-git repository.


## Requirements

* Fedora dist-git repository.
* Packit config file placed in the upstream repository.
* Pagure API tokens for Fedora Dist-git.
* Github API token.


## Tutorial

1. Pagure dist-git is configured in a way that it requires 2 API tokens in
   order to perform a pull request using the API (which packit is using).
   Please set these three environment variables using the appropriate tokens:
    1. `export PAGURE_USER_TOKEN=<token>` — this token is needed to access data
       in pagure. This is meant to be an API token of your user:
       https://src.fedoraproject.org/settings#nav-api-tab
    2. `export PAGURE_FORK_TOKEN=<token>` — packit needs this token to create a
       pull request:
       https://src.fedoraproject.org/fork/YOU/rpms/PACKAGE/settings#apikeys-tab
       If the fork does not exist, you have to create it in Pagure's web
       interface. We are working with Fedora team to relax this requirement.
    3. `export GITHUB_TOKEN=<token>` — you can obtain the token over here:
       https://github.com/settings/tokens

2. Files which are synced are mentioned in `.packit.yaml` as `synced_files` value.

3. Once you want to sync Fedora dist-git repo into the upstream repo,
   run `packit sync-from-downstream` in a working directory of your upstream
   repository:
    ```bash
    $ git clone https://github.com/user-cont/colin.git

    $ cd colin

    $ packit sync-from-downstream
    upstream active branch master
    Cloning repo: https://src.fedoraproject.org/rpms/colin.git -> /tmp/tmph9npe78e
    using master dist-git branch
    syncing /tmp/tmph9npe78e/colin.spec
    PR created: https://api.github.com/repos/phracek/colin/pulls/3
    ```


## `packit sync-from-downstream --help`

```
Usage: packit sync-from-downstream [OPTIONS] [PATH_OR_URL]

  Copy synced files from Fedora dist-git into upstream by opening a pull
  request.

  PATH_OR_URL argument is a local path or a URL to the upstream git
  repository, it defaults to the current working directory

Options:
  --dist-git-branch TEXT  Source branch in dist-git for sync.
  --upstream-branch TEXT  Target branch in upstream to sync to.
  --no-pr                 Pull request is not create.
  --fork / --no-fork      Push to a fork.
  --remote-name TEXT      Name of the remote where packit should push. if this
                          is not specified, it pushes to a fork if the repo
                          can be forked.
  -h, --help              Show this message and exit.
```
