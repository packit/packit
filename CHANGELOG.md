# 0.4.1

* Patch release with few fixes/minor changes.

# 0.4.0

## Features
* Packit service now submits builds in [copr](https://copr.fedorainfracloud.org) and once they're done it adds a GitHub status and comment with instructions how to install the builds.
* Packit service is now configurable via [jobs](https://github.com/packit-service/packit/blob/master/docs/configuration.md#packit-service-jobs) defined in configuration file.
* Packit is now able to check GPG signatures of the upstream commits against configured fingerprints.
* [CLI] `srpm` command now works also with [Source-git](https://packit.dev/source-git/).
* Fedmsg parsing has been unified into a single `listen-to-fedmsg` command.
* Packit service: Github webhook now reacts to ping event and validates payload signature.

## Fixes
* More source-git related changes have been applied.
* Few tracebacks when using CLI have been fixed.
* RPM package now really contains generated man pages.

## Minor
* Packit service runs on httpd server.
* [CLI] `status` command now access remote APIs asynchronously in parallel, which should speed up the execution.
* CLI now has `--dry-run` option to not perform any remote changes (pull requests or comments).
* Repository now includes Dockerfile and we by default use Docker instead of ansible-bender to build container image.
* Repository now includes Vagranfile.
* List of on-boarded projects has been moved to [README.md](https://github.com/packit-service/packit/blob/master/README.md#already-on-boarded)


# 0.3.0

We have a brand new website: https://packit.dev/!
[packit.dev repo](https://github.com/packit-service/packit.dev) contains source content for [Hugo website engine](https://gohugo.io).

## Features

* Packit supports [Source-git](https://packit.dev/source-git/).
* You can now specify your own actions to replace default packit behavior.
* Packit supports pagure.io-based upstream projects.
* Packit {propose-update, sync-from-downstream} supports copying directories.
* A new `status` command to display useful upstream/downstream info.
* You can now have a config file for packit in your home directory(`~/.config/packit.yaml`).
* Packit installed from an RPM now has manpages.

## Fixes

* Downstream pull requests titles now have correct version numbers.
* `sync-from-downstream` command constructs a PR correctly when origin is a fork.

## Minor

* Improved documentation.
* Code refactoring.
* Added MIT license notice into python files.
* CI shows code coverage and runs linters/checkers defined in pre-commit config file.
* We've started work on packit service by implementing a handler for a Github
  webhook. More to come in the next cycle!
* Packit is able to authenticate as a GitHub App.


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
