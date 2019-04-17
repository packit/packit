# 0.4.0

* README.md: add CoreOS to early adopters list
* Use flake8 args on alone rows
* Add files/packit.wsgi into pre-commit flake8 args
* Call web_hook application
* Add httpd and mod_wsgi for packit-service
* /webhooks/github/release reacts to ping event
* create_branch: check out if it exists
* [packit] sync from downstream branch 'master'
* Fix escaping of git patching
* Move specfile to subdir in tests
* Update upstream-ref option
* Fix double imports in tests
* Update packit/config.py
* Fix tests and use yaml config in sourcegit tests
* Add tests for sourcegit
* Fix and refactor tests
* Filter synced files in patches
* Add raw_files_to_sync property to SyncFilesConfig
* Add upstrem option to propose-update
* jobs: remove `from future` code
* bot_api: comment out WIP code
* address review from Jirka
* we don't like one-letter vars
* polish docs/conf
* docs for jobs
* docs,conf: simplify example config
* status: polish
* add tests for Steve
* Introduce Steve Jobs
* bring JobConfig to the next level
* add help for --debug
* [spec] Generating man pages during build needs all requirements
* Add multi-source example to docs
* Improve integration tests for sync files
* Use RawSyncFilesItem to more clear typing
* Add tests for sync
* Add docs for the sync methods
* Allow lists in the sync file source
* add jobs to our packit config
* -_- fix spec to 0.3.0
* recipe-tests: attempt a fix
* recipe: install more content from RPM
* containerized tests: comment out and document

# 0.3.0

We have a brand new website: https://packit.dev/! [packit.dev repo](https://github.com/packit-service/packit.dev) contains source content for [Hugo website engine](https://gohugo.io).

## Features

* Packit supports [Source-git](https://packit.dev/source-git/).
* You can now specify your own actions to replace default packit behavior.
* Packit supports pagure.io-based upstream projects.
* Packit {propose-update, sync-from-downstream} supports copying directories.
* A new command `status`! It displays useful upstream/downstream info.
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
