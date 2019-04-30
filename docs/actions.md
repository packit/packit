# Actions

You can probably find yourself in a situation where some part of the packit workflow needs to be
tweaked for your package.

Packit supports some actions, that can be defined in the configuration file.
The part of the default behaviour is then skipped, and the configured command is called instead.

There are also some hooks presented -- it works as an action without any default behaviour.

Currently, there are the following actions that you can use:

### propose-update

|        | name                  | working directory | when run                                                                          | description                               |
| ------ | --------------------- | ----------------- | --------------------------------------------------------------------------------  | ----------------------------------------- |
| [hook] | `post-upstream-clone` | upstream git repo | after cloning of the upstream-repo (master) and before other operation            |                                           |
| [hook] | `pre-sync`            | upstream git repo | after cloning of the upstream-repo and checkout to the right (release) branch     |                                           |
|        | `prepare-files`       | upstream git repo | after clone and checkout of upstream and dist-git repo                            | replace patching and archive generation   |
|        | `create-patches`      | upstream git repo | after sync of upstream files to the downstream                                    | replace patching                          |
|        | `create-archive`      | upstream git repo | when the archive needs to be created                                              | replace the code for creating an archive  |
|        | `get-current-version` | upstream git repo | when the current version needs to be found                                        | expect version as a stdout                |


### srpm

|        | name                  | working directory | when run                                                                          | description                               |
| ------ | --------------------- | ----------------- | --------------------------------------------------------------------------------  | ----------------------------------------- |
| [hook] | `post-upstream-clone` | upstream git repo | after cloning of the upstream-repo (master) and before other operation            |                                           |
|        | `get-current-version` | upstream git repo | when the current version needs to be found                                        | expect version as a stdout                |
|        | `create-archive`      | upstream git repo | when the archive needs to be created                                              | replace the code for creating an archive  |
|        | `create-patches`      | upstream git repo | after sync of upstream files to the downstream                                    | replace patching                          |


-----

In your package config they can be defined like this:

```yaml
specfile_path: package.spec
synced_files:
  - packit.yaml
  - package.spec
upstream_project_name: package
downstream_package_name: package
dist_git_url: https://src.fedoraproject.org/rpms/package.git
actions:
  prepare-files: "make prepare"
  create-archive: "make archive"
```
