# 0.2.0


## Breaking Changes

* We have renamed two variables in our configuration file:
  * `package_name` → `downstream_package_name`
  * `upstream_name` → `upstream_project_name`

## Features

* You can now use packit to sync files from your dist-git repo into upstream
  (mainly to keep spec files in sync). `sync-from-downstream` is the command.
* An SRPM can be created out of the current content in your upstream repository
  — please check out the `srpm` command.
* Packit is able to create bodhi updates using the `create-update` command.
* You can ask packit to build the latest content of your dist-git
  repository in koji: the command is `build`.
* We have added `--force-new-sources` option to propose-update update command
  to bypass our caching optimization.
* `propose-update` command now has option `--local-content` which disables
  checking out the tag with the upstream release. This is useful if you forget
  to bump your spec file when doing a release.
* You are now able to pick a specific upstream release version in
  `propose-update` command.

## Fixes

* Packit checks if the upstream tarball is already present in the lookaside
  cache so it's not uploaded twice. We have fixed a behavior when the upload
  part was skipped while having old tarball specified in dist-git. Packit now
  does the right thing - checks if sources file has the correct tarball
  referenced.
* We have updated several error messages which were coming from GitPython and
  it was not clear what's wrong.

## Minor

* We have added CONTRIBUTING.md to ease contribution to packit. All your
  patches are welcome!
* We are now using black, flake8 and mypy to improve code quality.
* We have moved some info from README to dedicated doc. Also, all the
  documentation should be up to date.


# 0.1.0

The first official release of packit!


## Features

* `packit propose-update` brings a new upstream release into Fedora rawhide.
  For more info, please [check out the documentation](/docs/update.md).

* `packit watch-releases` listens to github events for new upstream releases.
  If an upstream project uses packit, it would bring the upstream release into
  Fedora, the same way as `packit propose-update`. Please make sure that your
  upstream project is set up using
  [github2fedmsg](https://apps.fedoraproject.org/github2fedmsg/).
