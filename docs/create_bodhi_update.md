# `packit create-update`

Create a new bodhi update for the latest Fedora build of the upstream project.


## Requirements

* Upstream git repository on Github.
* Packit config file placed in the upstream repository.
* Valid Fedora Kerberos ticket.


## Tutorial

1. [Place a config file for packit in the root of your upstream repository.](/docs/configuration.md).

2. Once the [builds are done](build.md), you can run the `create-update` command.
   If you don't specify the koji builds packit takes latest build.
   ```bash
   $ packit create-update --dist-git-branch f29 https://github.com/packit-service/packit.git
   Bodhi update FEDORA-2019-b72add0dcd:
   - https://bodhi.fedoraproject.org/updates/FEDORA-2019-b72add0dcd
   - stable_karma: 3
   - unstable_karma: -3
   - notes: "New upstream release 0.1.0"
   ```


## `packit create-update --help`

```
Usage: packit create-update [OPTIONS] [PATH_OR_URL]

  Create a bodhi update for the selected upstream project

  PATH_OR_URL argument is a local path or a URL to the upstream git
  repository, it defaults to the current working directory

Options:
  --dist-git-branch TEXT          Target branch in dist-git to release into.
  --koji-build TEXT               Koji build (NVR) to add to the bodhi update
                                  (can be specified multiple times)
  --update-notes TEXT             Bodhi update notes
  --update-type [security|bugfix|enhancement|newpackage]
                                  Type of the bodhi update
  -h, --help                      Show this message and exit.
```
