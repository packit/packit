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

 Key name             | type            | description
----------------------|-----------------|----------------------------------------------------------------------
 `specfile_path`      | string          | relative path to a spec file within the upstream repository
 `synced_files`       | list of strings | a list of relative paths to files in the upstream repo which are meant to be copied to dist-git during an update
 `upstream_name`      | string          | name of the upstream repository
 `package_name`       | string          | name of package in Fedora
 `dist_git_url`       | string          | URL of the corresponding dist-git repository


## Minimal sample config

This is a sample config which is meant for packit itself.

```yaml
specfile_path: packit.spec
synced_files:
  - packit.spec
upstream_name: packit
package_name: packit
dist_git_url: https://src.fedoraproject.org/rpms/packit.git
```

## In-progress work

You may see packit configs whith much more values, such as jobs and checks
keys. Packit is not using those values right now.
