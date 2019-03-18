# `packit build`

Submit a koji build for the selected branch in Fedora dist-git.


## Requirements

* Upstream git repository on Github.
* Packit config file placed in the upstream repository.
* Valid Fedora Kerberos ticket.


## Tutorial

1. [Place a config file for packit in the root of your upstream repository.](/docs/configuration.md)

2. The command below would perform `fedpkg build` in the Fedora dist-git master branch.
   ```bash
   $ cd my/ustream/project/
   $ packit build
   ```


## `packit build --help`

```
Usage: packit build [OPTIONS] [PATH_OR_URL]

  Build selected upstream project in Fedora.

  Packit goes to dist-git and performs `fedpkg build` for the selected
  branch.

  PATH_OR_URL argument is a local path or a URL to the upstream git
  repository, it defaults to the current working directory

Options:
  --dist-git-branch TEXT  Target branch in dist-git to release into.
  --dist-git-path TEXT    Path to dist-git repo to work in. Otherwise clone
                          the repo in a temporary directory.
  --scratch               Submit a scratch koji build
  -h, --help              Show this message and exit.
```
