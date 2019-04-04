# Actions that can be redefined by the user

|        | name                  | working directory | when run                                                                          | description                               |
| ------ | --------------------- | ----------------- | --------------------------------------------------------------------------------  | ----------------------------------------- |
| [hook] | `init`                | upstream git repo | after cloning of the upstream-repo (master) and before other operation            |                                           |
| [hook] | `pre-sync`            | upstream git repo | after cloning of the upstream-repo and checkout to the right (release) branch     |                                           |
|        | `prepare-files`       | upstream git repo | after clone and checkout of upstream and dist-git repo                            | replace patching and archive generation   |
|        | `patch`               | upstream git repo | after sync of upstream files to the downstream                                    | replace patching                          |
|        | `create-archive`      | upstream git repo | when the archive needs to be created                                              | replace the code for creating an archive  |
|        | `get-current-version` | upstream git repo | when the current version needs to be found                                        | expect version as a stdout                |
