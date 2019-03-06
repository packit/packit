# `packit propose-update`

This is a detailed documentation for the update functionality of packit.


## Requirements

* Packit config file placed in the upstream repository.
* Spec file present in the upstream repository.
* Pagure API tokens for Fedora Dist-git.
* Valid Fedora Kerberos ticket.


## Tutorial

1. Place a file called `.packit.yaml` or `packit.yaml` in the root of your upstream repository.
    * The configuration is described [in this document](/docs/configuration.md). TBD: write it!
    * Please get inspired from [an existing
      config](https://github.com/user-cont/colin/blob/master/.packit.yaml) in
      colin project.

2. Place a spec file into your upstream project (and make sure that
   `specfile_path` in the config has a correct value).
    * This spec file will be then used to perform the update.
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
       If the fork does not exist, you have to create it.

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
Usage: packit_base.py propose-update [OPTIONS]

  Release current upstream release into Fedora

Options:
  --dist-git-branch TEXT  Target branch in dist-git to release into.
  --dist-git-path TEXT    Path to dist-git repo to work in.
  -h, --help              Show this message and exit.
```

