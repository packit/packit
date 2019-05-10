# Configuration for packit

## Project's configuration file

Packit uses a configuration file in the upstream repository. The config file is written in YAML language.

You should place the file in the root of your upstream repo. Packit accepts these names:
* `.packit.yaml`
* `.packit.yml`
* `.packit.json`
* `packit.yaml`
* `packit.yml`
* `packit.json`


### Values

 Key name                  | Type            | Description
---------------------------|-----------------|----------------------------------------------------------------------
 `specfile_path`           | string          | relative path to a spec file within the upstream repository (mandatory)
 `synced_files`            | list of strings | a list of relative paths to files in the upstream repo which are meant to be copied to dist-git during an update
 `upstream_project_name`   | string          | name of the upstream repository (e.g. in PyPI); this is used in `%prep` section
 `upstream_ref`            | string          | git reference to last upstream git commit (for source-git repos)
 `downstream_package_name` | string          | name of package in Fedora (mandatory)
 `dist_git_namespace`      | string          | namespace in dist-git URL (defaults to "rpms")
 `dist_git_base_url`       | string          | URL of dist-git server, defaults to "https://src.fedoraproject.org/" (has to end with a slash)
 `create_tarball_command`  | list of strings | a command which generates upstream tarball in the root of the upstream directory (defaults to `git archive -o "{package_name}-{version}.tar.gz" --prefix "{package_name}-{version}/" HEAD`)
 `current_version_command` | list of strings | a command which prints current upstream version (hint: `git describe`) (defaults to `git describe --tags --match '*.*'`)
 `actions`                 | string:string   | custom actions/hooks overwriting the default behavior of the workflow (more in [Actions](./actions.md))
 `jobs`                    | list of dicts   | a list of job definitions for packit service. See below for details
 `allowed_gpg_keys`        | list of strings | a list of gpg-key fingerprints; if specified. One of the configured keys have to sign the last commit when syncing release or pull-request. Add GitHub key (`4AEE18F83AFDEB23`) if you want to use this on code merged via GitHub web interface.


### Minimal sample config

This is a sample config which is meant for packit itself.

```yaml
specfile_path: packit.spec
synced_files:
  # Copy a file from root of the upstream repo to dist-git.
  - packit.spec
  # src: a file in root of the upstream repository
  # dest: path within the downstream repository
  - src: packit.spec
    dest: redhat/packit.spec
  # also supports globbing
  - src: *.md
    dest: docs/
  # you can specify multiple source files as well:
  - src:
    - doc1.md
    - doc2.md
    dest: docs/
upstream_project_name: packitos
downstream_package_name: packit
```


### Packit service jobs

**Packit service is not live, we are working hard to deploy it by the end of April.**

Once the service starts handling events of your repository, it needs to have a clear definition of what it should do.

The tasks the packit service should do are defined in section `jobs`. This is a list of dicts.

Every job has two mandatory keys:

1. `job` - name of the job (you can imagine this as a CLI command)
2. `trigger` - what is the trigger for the job?

Every job only supports a specific set of triggers.

Jobs can also accept additional configuration in a dict `metadata`.


#### Supported jobs

**propose\_downstream**

Take the new upstream release and land it in Fedora.

Supported triggers: **release**.

Additional configuration set in the `metadata` section:
* `dist_git_branch`: name of the dist-git branch where the PR should be opened.


**Example**

```yaml
jobs:
- job: propose_downstream
  trigger: release
  metadata:
    dist_git_branch: master
- job: propose_downstream
  trigger: release
  metadata:
    dist_git_branch: f30
```

With this configuration, packit service would react to new upstream releases
and create dist-git pull requests for master and f30 branches with the
content of the upstream release.


**sync\_from\_downstream**

Pick up a change (mass rebuild, proven packager rebuild or fix) from Fedora
dist-git and send it to upstream repository.

Supported triggers: **commit**.


**Example**

```yaml
jobs:
- job: sync_from_downstream
  trigger: commit
```

**copr\_build**

Gather data from new pull_request or release and use trigger new copr build with it.

Supported triggers: **pull_request**, **release**.


**Example**

```yaml
jobs:
- job: copr_build
  trigger: pull_request
  metadata:
    targets:
      - fedora-rawhide-x86_64
      - fedora-30-x86_64

```

### In-progress work

You may see packit configs with more values: support for checks is work in progress.
Packit is not using those values right now.


## User configuration file

When running packit as a tool locally, it is convenient to use a configuration
file to provide data such as API tokens. Packit respects `XDG_CONFIG_HOME`
environment variable. If not set, it looks inside `~/.config/` directory.

The acceptable names are the same as for the package config:
* `.packit.yaml`
* `.packit.yml`
* `.packit.json`
* `packit.yaml`
* `packit.yml`
* `packit.json`


### Values

 Key name                     | Type            | Description
------------------------------|-----------------|----------------------------------------------------------------------
 `debug`                      | bool            | enable debug logs
 `dry_run`                    | bool            | Do not perform any remote changes (pull requests or comments)
 `fas_user`                   | string          | username in Fedora account system (to perform kinit if needed)
 `keytab_path`                | string          | path to a Kerberos keytab file (requires `fas_user` to be set)
 `github_token`               | string          | Github API token: this is needed when packit interacts with Github API
 `pagure_user_token`          | string          | Pagure token needed to access REST API, get it at: https://src.fedoraproject.org/settings#nav-api-tab
 `pagure_fork_token`          | string          | a token so packit can create a pull request: https://src.fedoraproject.org/fork/YOU/rpms/PACKAGE/settings#apikeys-tab
 `github_app_id`              | string          | github app ID used for authentication
 `github_app_cert_path`       | string          | path to a certificate associated with a github app
 `webhook_secret`             | string          | when specified in a Github App settings, GitHub uses it to create a hash signature with each payload

You can also specify the tokens as environment variables: `GITHUB_TOKEN`, `PAGURE_USER_TOKEN`, `PAGURE_FORK_TOKEN`.

Keys related to Github app are meant for a packit service deployment.


### Minimal sample config

```yaml
debug: true
github_token: mnbvcxz123456
pagure_user_token: qwertyuiop098765
```
