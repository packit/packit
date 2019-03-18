# `packit propose-update`

This is a detailed documentation for the update functionality of packit. The
command creates a new pull request in Fedora using a selected or latest
upstream release.


## Requirements

* Upstream git repository on Github.
* Upstream release (read, git tag) where version in spec file is equivalent to
  the name of the git tag.
* Packit config file placed in the upstream repository.
* Spec file present in the upstream repository and is correct in a given
  release.
* Pagure API tokens for Fedora Dist-git.
* Github API token.
* Valid Fedora Kerberos ticket.


## Tutorial

1. Place a file called `.packit.yaml` or `packit.yaml` in the root of your upstream repository.
    * The configuration is described [in this document](/docs/configuration.md).
    * Please get inspired from [an existing
      config](https://github.com/user-cont/colin/blob/master/.packit.yaml) in
      colin project.

2. Place a spec file into your upstream project (and make sure that
   `specfile_path` in the config has a correct value).
    * This spec file will be then used to perform the update in Fedora.
    * When you create a new upstream release, you should also update the spec file.
    * Once your upstream release is out (and the spec file is really up to
      date), you can use packit to release it into Fedora.

3. Create a new upstream release. The spec file needs to be included in the ref
   for upstream release, because packit checks out the tag for the upstream
   release before copying files downstream.

4. Pagure dist-git is configured in a way that it requires 2 API tokens in
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

5. Once you have performed the upstream release (and the new archive is up),
   run `packit propose-update` in a working directory of your upstream
   repository:
    ```bash
    $ git clone https://github.com/user-cont/colin.git

    $ cd colin

    $ packit propose-update
    using "master" dist-git branch
    syncing ./colin.spec
    INFO: Downloading file from URL https://files.pythonhosted.org/packages/source/c/colin/colin-0.3.0.tar.gz
    100%[=============================>]     3.18M  eta 00:00:00
    downloaded archive: /tmp/tmpaanrpgjz/colin-0.3.0.tar.gz
    uploading to the lookaside cache
    PR created: https://src.fedoraproject.org/rpms/colin/pull-request/4
    ```


## `packit propose-update --help`

```
Usage: packit propose-update [OPTIONS] [PATH_OR_URL] [VERSION]

  Release current upstream release into Fedora

  PATH_OR_URL argument is a local path or a URL to the upstream git
  repository, it defaults to the current working directory

  VERSION argument is optional, the latest upstream version will be used by
  default

Options:
  --dist-git-branch TEXT  Target branch in dist-git to release into.
  --dist-git-path TEXT    Path to dist-git repo to work in. Otherwise clone
                          the repo in a temporary directory.
  --local-content         Do not checkout release tag. Use the current state
                          of the repo.
  --force-new-sources     Upload the new sources also when the archive is
                          already in the lookaside cache.
  -h, --help              Show this message and exit.
```
