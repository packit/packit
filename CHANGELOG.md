# 0.3.0

* change: do not require synced_files in packit.yaml
* sensible __repr__ for SyncF classes
* ehm, actually use package_config.specfile_path
* git describe: use --match *
* sg: add a link to real sg repo
* Update configuration.md with pykickstart
* Update configuration.md with proper link
* Add more docs for actions
* Add tests for ActionName enum and fix the existing ones
* Use enum for actions
* Use Upstream in upstream_with_actions fixture
* Add table of hooks/actions
* Do not call pytest fixtures directly
* Add another hook for pykickstart
* Fixes after rebase
* Add tests for action handling
* Move methods for actions to base class for Upstream/Distgit
* path_or_url: fix tests, we no longer do HEAD request
* test covers Status.get_builds
* Add OSBS to the early adoption candidate
* debug logs added
* changed _is_url and added tests
* giturlparse replaced by regex
* move generic content to our website
* Move bodhi reposnse into alone python module
* contributing: update info about minimum version of bender
* webhook: new endpoint to get health
* webook: accept only new release events
* add functional test for the webhook
* add requests to requirements
* tune the webhook a bit more
* local development in a cont for packit service
* make packit-service work in openshift
* tests: fix pagure E2E test
* Tests for status: get_downstream_prs and get_updates
* [cli/status.py] better docstring
* more sensible tests for files_to_sync
* suggestions should be CI-tested!
* Jirka rocks!
* sync-from-downstream: improve help descriptions
* propose-update: don't bail if there are only untracked files
* pass upstream_local_project from cli to API
* [CONTRIBUTING.md] evil pre-commit
* Add into tox.ini PYTHONDONTWRITEBYTECODE
* src value in .packit.yaml support also directories src: fedora/tests/
* Fixes #188 Add license MIT text into python files
* Remove leftover empty line
* Implement SyncFilesConfig __eq__ method
* Fixes #171: Packit supports copying directories
* Fix test
* Fixes #157 Create common ancestor for Gits
* Franta is a nit picker.
* Comment packit_base()
* document running packit from git directly
* Fix after the rebase
* Add test for loading actions from config
* Load actions from config
* Use actions in upstream/downstream
* Add method for checking action presence
* Use actions in API
* Add method for checking existence
* Restructure the API methods
* Fix format and typing after rebase
* Fix self.up/self.dg after replace in API
* Fix fedpkg imports
* Add docstring for PackageConfig.get_output_from_action
* Get support for actions in the PackageConfig
* Remove unused utils function
* Move fedpkg to other file
* get user config: stop when found
* enable auth as a github app
* Pick latest version when not specified (URM vs. spec)
* status: fix get_dg_versions
* create new file for status methods
* add message for no upstream releases
* list bodhi updates using tabulate
* move functionality to api
* pre-commit update
* change logger to echo
* packit status: downstream PRs, DG versions, upstream releases, latest builds
* initial work on status cmd
* [spec] generate man pages with click-man
* [setup.cfg] We don't want universal wheels, since we don't support Python 2
* docs/configuration.md: add yaml to code block
* pre-commit
* a test case for get_user_config
* document user config
* config: annotate properties, more logging
* drop pagure_package_token value: we're not using it
* document mandatory config values
* Implement basic web-hook
* fix tests
* make downstream_project_url optional
* sync-from-ds: push to fork by default
* api: make upstream & distgit properties
* refactor and simplify api.sync_from_downstream
* recipe: set metadata in the playbook
* [sg2dg & sg2srpm] comment all out
* [Jenkinsfile] run pre-commit
* [tox.ini] run coverage
* Improve docstring for LocalProject
* Rework tests for LocalProject
* Add refresh to LocalProject
* Use more explicit method names in LocalProject
* Refactor parsing path_or_url in LocalProject
* Refactor the LocalProject
* Add missing new-line in bodhi output
* config: Remove PackageConfig leftovers from Config
* Implement reading user config from file
* recipe: set metadata in the playbook
* rebase-helper: use get_version instead of get_full_version
* Give dist-git url to PagureService
* docs/conf: show more packit.yaml examples
* address comments from Franta
* Review comments from Jirka
* 0.2.0 release blog post
* Drop anymarkup, yaml.safe_load() is all we need

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
