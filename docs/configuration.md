# Packit configuration file

Packit uses a configuration file in the upstream repository. The config file is written in YAML language.

You should place the file in the root of your upstream repo. Packit accepts these names:
* `.packit.yaml`
* `.packit.yml`
* `.packit.json`
* `packit.yaml`
* `packit.yml`
* `packit.json`


## Values

 Key name                  | type            | description
---------------------------|-----------------|----------------------------------------------------------------------
 `specfile_path`           | string          | relative path to a spec file within the upstream repository
 `synced_files`            | list of strings | a list of relative paths to files in the upstream repo which are meant to be copied to dist-git during an update
 `upstream_project_name`   | string          | name of the upstream repository (e.g. in PyPI); this is used in `%prep` section
 `downstream_package_name` | string          | name of package in Fedora
 `dist_git_namespace`      | string          | namespace in dist-git URL (defaults to "rpms")
 `dist_git_base_url`       | string          | URL of dist-git server, defaults to "https://src.fedoraproject.org/" (has to end with a slash)
 `create_tarball_command`  | list of strings | a command which generates upstream tarball in the root of the upstream directory (defaults to `git archive -o "{package_name}-{version}.tar.gz" --prefix "{package_name}-{version}/" HEAD`)
 `current_version_command` | list of strings | a command which prints current upstream version (hint: `git describe`) (defaults to `git describe --tags --match '*.*'`)


## Minimal sample config

This is a sample config which is meant for packit itself.

```yaml
specfile_path: packit.spec
synced_files:
  - packit.spec
# packit was already taken on PyPI
upstream_project_name: packitos
downstream_package_name: packit
```

## Real examples

The list of projects which already have packit config in their upstream repositories:
* [packit-service/packit](https://github.com/packit-service/packit/blob/master/.packit.yaml)
* [packit-service/ogr](https://github.com/packit-service/ogr/blob/master/.packit.yaml)
* [user-cont/colin](https://github.com/user-cont/colin/blob/master/.packit.yaml)
* [user-cont/conu](https://github.com/user-cont/conu/blob/master/.packit.yaml)
* [TomasTomecek/sen](https://github.com/TomasTomecek/sen/blob/master/.packit.yaml)
* [rebase-helper/rebase-helper](https://github.com/rebase-helper/rebase-helper/blob/master/.packit.yaml)


## In-progress work

You may see packit configs with much more values, such as jobs and checks
keys. Packit is not using those values right now.
