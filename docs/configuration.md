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
 `downstream_package_name` | string          | name of package in Fedora (mandatory)
 `dist_git_namespace`      | string          | namespace in dist-git URL (defaults to "rpms")
 `dist_git_base_url`       | string          | URL of dist-git server, defaults to "https://src.fedoraproject.org/" (has to end with a slash)
 `create_tarball_command`  | list of strings | a command which generates upstream tarball in the root of the upstream directory (defaults to `git archive -o "{package_name}-{version}.tar.gz" --prefix "{package_name}-{version}/" HEAD`)
 `current_version_command` | list of strings | a command which prints current upstream version (hint: `git describe`) (defaults to `git describe --tags --match '*.*'`)
 `actions`                 | string:string   | custom actions/hooks overwriting the default behavior of the workflow (more in [Actions](./actions.md))

### Minimal sample config

This is a sample config which is meant for packit itself.

```yaml
specfile_path: packit.spec
synced_files:
# possible styles how to write a file to sync
  # Copy the file in an upstream directory into the same downstream directory.
  # File name is not changed
  - packit.spec
  # src means a source file in root from the upstream directory.
  # dest means a directory and filename into the downstream directory.
  # in this case the name is the same
  - src: packit.spec
    dest: redhat/packit.spec
  # src means all md files in a root from the upstream directory
  # dest means all md files are copied into the downstream docs directory.
  - src: *.md
    dest: docs/
# packit was already taken on PyPI
upstream_project_name: packitos
downstream_package_name: packit
```

### Real examples

The list of projects which already have packit config in their upstream repositories:
* [packit-service/packit](https://github.com/packit-service/packit/blob/master/.packit.yaml)
* [packit-service/ogr](https://github.com/packit-service/ogr/blob/master/.packit.yaml)
* [user-cont/colin](https://github.com/user-cont/colin/blob/master/.packit.yaml)
* [user-cont/conu](https://github.com/user-cont/conu/blob/master/.packit.yaml)
* [TomasTomecek/sen](https://github.com/TomasTomecek/sen/blob/master/.packit.yaml)
* [rebase-helper/rebase-helper](https://github.com/rebase-helper/rebase-helper/blob/master/.packit.yml)
* [dcantrell/pykickstart](https://github.com/dcantrell/pykickstart/blob/master/packit.yaml)


### In-progress work

You may see packit configs with much more values, such as jobs and checks
keys. Packit is not using those values right now.


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
 `fas_user`                   | string          | username in Fedora account system (to perform kinit if needed)
 `keytab_path`                | string          | path to a Kerberos keytab file (requires `fas_user` to be set)
 `github_token`               | string          | Github API token: this is needed when packit interacts with Github API
 `pagure_user_token`          | string          | Pagure token needed to access REST API, get it at: https://src.fedoraproject.org/settings#nav-api-tab
 `pagure_fork_token`          | string          | a token so packit can create a pull request: https://src.fedoraproject.org/fork/YOU/rpms/PACKAGE/settings#apikeys-tab
 `github_app_installation_id` | string          | if authenticating with a github app, this is the installation ID
 `github_app_id`              | string          | github app ID used for authentication
 `github_app_cert_path`       | string          | path to a certificate associated with a github app

You can also specify the tokens as environment variables: `GITHUB_TOKEN`, `PAGURE_USER_TOKEN`, `PAGURE_FORK_TOKEN`.

Keys related to Github app are meant for a packit service deployment.


### Minimal sample config

```yaml
debug: true
github_token: mnbvcxz123456
pagure_user_token: qwertyuiop098765
```
