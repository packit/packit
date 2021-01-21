# 0.24.0

- No user-facing changes done in this release.

# 0.23.0

- The `propose-update` has been renamed to `propose-downstream`; `propose-update` is now deprecated
  to unify the naming between CLI and service. ([@jpopelka](https://github.com/jpopelka), [#1065](https://github.com/packit-service/packit/pull/1065))
- Our README has been cleaned and simplified. ([@ChainYo](https://github.com/ChainYo), [#1058](https://github.com/packit-service/packit/pull/1058))
- The :champagne: comment with the installation instructions has been disabled by default. ([@mfocko](https://github.com/mfocko), [#1057](https://github.com/packit-service/packit/pull/1057))
  - More information can be found in [our documentation](https://packit.dev/docs/configuration/#notifications).
- Packit is being prepared to be released in EPEL 8 so it can be consumed in RHEL and CentOS Stream. ([@nforro](https://github.com/nforro), [#1055](https://github.com/packit-service/packit/pull/1055))

# 0.22.0

- `packit init` introduces the `--upstream-url` option. When specified,
  `init` also sets up a source-git repository next to creating a configuration file.
- Don't rewrite macros when setting release and version in spec file.
- Fix generation of Copr settings URL for groups.
- Improve processing of the version when proposing a Fedora update.

# 0.21.0

- If the first `Source` tag in a spec file is not indexed, it is always returned,
  no matter the value of `source_name`.
- Sanitize potentially problematic characters in a branch name
  before creating a copr project name from it.
- Default job now includes copr build as well.

# 0.20.0

- The `fedora-all`, `fedora-stable`, `fedora-development` and `epel-all`
  chroot aliases are now translated to concrete chroots by consulting Bodhi,
  making the transition to new Fedora releases smoother.
- A new, `copy_upstream_release_description` option is available in
  `packit.yaml`. When set to `true`, the GitHub release description is going
  to be used to update the changelog in the spec-file, when creating a new
  update in Fedora dist-git. When set to `false` (the default), the subject
  lines of the commits included in the release are used to update the changelog.
- Fix an issue (#1012) by improving how the current version is discovered.

# 0.19.0

- Allow syncing full content of the spec-file.
- Let packit create empty patch files from empty commits.
- Check for the existing pull requests in distgit when using `propose-update`.
- Allow symlinking absolute path to the archive within repository.

# 0.18.0

- Packit got new `archive_root_dir_template` config option to get custom archive root dir. You can find more info [in the documentation](https://packit.dev/docs/configuration/#archive_root_dir_template).

# 0.17.0

## Minor changes and fixes

- When adding patches to a specfile, the numbering of source-git patches begins after original patches.
- It is now possible to use globbing pattern when specifying ref in packit config.
- `upstream_tag_template` is now used for extracting version from git tag.
- Specifiying project using CLI is fixed.
- Packit doesn't drop leading zeros in version strings.
- Our contribution guidelines are cleaned up.
- `--remote` option is now global and available to all the commands.
- `sync-from-downstream --remote` was renamed to `--remote-to-push`.
- `--remote` can now be specified in user's config (via
  `upstream_git_remote` parameter).
- packit is now able to generate a patch file with format-patch without leading a/ and b/ in the patch diff.

# 0.16.0

## Minor changes and fixes

- Correctly log output when using sandcastle (packit-service) since it returns a single string instead of a list.
- Improve action output logging: you will see the output from actions by default.
- Allow having different job definitions for multiple chroots in Copr.

# 0.15.0

## Minor changes and fixes

- `copr-build` CLI command has new `request-admin-if-needed` option. If you specify it,
  we ask for the admin access to the Copr project in case we can't edit the settings of the project.
- Creating archive with custom command was fixed.
  The archive was not found when building SRPM because of the incorrect processing of the paths from the command output.
- Logs related to SRPM creation and Copr project handling are improved.

# 0.14.0

- Reverted "invoke all commands in shell" change that had been introduced in 0.13.0.

# 0.13.1

# Bug fixes

- Fix a programming error in `validate-config`, which caused the sub-command
  to fail when checking Packit configuration files.
- Prioritize including the PR ID in the release field over the Git ref when
  creating a SRPM from the current checkout.
- Fix a programming error when updating the `%changelog` with the subject
  lines of the commits since the last tag.

# 0.13.0

## Features

- Commands from actions run in a shell by default; adding `bash -c` is no
  longer required.
- The name of the branch is included in the release field when creating a SRPM
  from current checkout.
- Packit configuration can be checked using the new `validate-config`
  subcommand.
- If possible, use the subject lines of the commits since the last tag when
  updating `%changelog`.
- Use patch metadata when generating patch files for dist-git.

## Minor changes and fixes

- Improved logs by adding `__repr__()` to multiple classes.
- Fixed setting of default values in job configurations.

# 0.12.0

## Features

- Users are now able to set some additional properties for COPR projects created via `copr-build` command,
  e.g. visibility on the Copr homepage and persistence.

## Minor changes and fixes

- Log RebaseHelper error messages.

# 0.11.1

## Minor changes and fixes

- Enabled copr build against master branch. For more details please check [readme](https://github.com/packit-service/packit#installation).
- Error and log messages improvements.

# 0.11.0

## Features

- Fedora 32 is now part of the `fedora-stable` alias and Fedora 30 is no longer included in the stable variant.
- There is an `epel-all` alias available.

## Minor changes and fixes

- The logs which packit produces are now more consistent and have unified format.
- When doing `propose-update` while upstream and downstream spec files differ, it could happen that the downstream spec would not be processed correctly. This is now fixed, for more info see [packit#828](https://github.com/packit-service/packit/issues/828).
- Kerberos-related code was re-organized for sake of the upcoming koji work - this shouldn't affect any functionality.

# 0.10.2

## Minor changes and fixes

- Fixed test error caused by missing git configuration #794

# 0.10.1

A patch release, which fixes/improves some job metadata fields:

- `dist_git_branch` (see [0.10.0](#0100)) has been renamed to `dist_git_branches` and it accepts also a list of values.
- New `scratch` option that will be used for Koji builds.
- New `branch` option that will be used for specifying a branch for which we want to run builds.

# 0.10.0

## Features

- We are able to linearize (and create patches from) extremely complex source-git repos.
- Job metadata in `.packit.yaml` are now being validated.
  - `dist-git-branch` key has been renamed to `dist_git_branch`

## Minor changes and fixes

- We no longer inspect archive extension set in `Source` and create `.tar.gz` by default.
  - This should be more flexible and prevent issues for “non-standard” archive names.
- `propose-update` creates downstream spec if it’s not there
  - This used to happen when using packit on a newly created package in Fedora which did not have spec file added yet.
- Fix for web URLs for Copr builds owned by groups.
- Marshmallow v3 is now supported as well.

# 0.9.0

## Features

- CLI has a new `local-build` command.
- Packit learned how to look for RPM spec files on its own, so specifying `specfile_path` in the configuration is not mandatory anymore.
- Default configuration has `tests` job enabled from now on. You still need to use `fmf` to create some tests, otherwise testing-farm only tests the success of the installation.
- We don't touch `Version` in spec files and change `Release` only by default.

## Minor changes and fixes

- Improved documentation (README & CONTRIBUTING).
- `copr-build` CLI command has new `--upstrem-ref` option.
- As a result of `keys.fedoraproject.org` being turned off, Packit now tries a list of GPG keyservers when downloading keys to check commit signatures.
- `generate` CLI command is now deprecated in favor of the `init` command.
- When executing `copr-build` command, you don't need to set project name if this value is defined in `copr_build` job in configuration file.
- When loading authentication in the config file - users are warned only if deprecated keys are used, no more confusing messages when you do not have authentication key in the configuration.
- Several `source-git` related fixes & improvements are applied.
- A bug which was causing SRPM-build failures in Packit Service for projects which had their spec files stored in a subdirectory is fixed.
- We handle `git-describe` output better: it should help when tags contain dashes.

# 0.8.1

## Features:

- Packit is able to build in [Koji](https://koji.fedoraproject.org) from upstream/source-git.
- CLI has bash-completion.
- Configuration can use a new option (`patch_generation_ignore_paths`) to exclude paths from patching.

# 0.8.0

Packit has a [new logo](https://github.com/packit-service/packit/blob/master/design/export/logo.svg)!

## Features:

- Marshmallow object schema was implemented.
- `config file` and `spec file` are synced by default.
- We use testing farm for sanity tests.
- `packit status` command shows latest copr builds.
- Target aliases (currently fedora-development, fedora-stable, fedora-all) can now be used in the packit config file.
- `upstream_package_name` and `downstream_package_name` are no longer required in package config. github repository name is the default value both.
- If no jobs are defined in .packit.yaml, packit by default runs build job on fedora-stable targets and propose_downstream on fedora-all branches.
- Image version of packit is now fedora 31
- packit can now download URL package sources before SRPM build.
- When doing a new update in Fedora dist-git, packit now by default creates a new pull request instead of pushing directly to dist-git.
- Build command has nicer output.
- `create-archive` uses fullpath for validation and splits long lines of output.
- SRPM runs also in a repo with detached head.
- Log output from subprocesses is in realtime.
- Specfile is refreshed after each run of the propose-update.
- When there is no copr project owner, exception is raised
- While building specfile from custom specfile, the archive is linked from the spec-directory.
- Setting cwd in command handlers is allowed.
- SRPM build is run from the folder containing specfile.

## Fixes:

- Consecutive API call for status works.
- rebase-helper breaking changes in new version is fixed.
- fixed updating version on srpm build

## Minor:

- pre-commit check requires rebased branch.
- fedora version in .packit.yaml config is updated.
- Code related to copr id now extracted to dedicated class.
- There is a warning in logs when there is no packit config in repository.
- Tests are now restructured and use new structure or `requre`, also containing tests for copr.
- The stale bot is now set with up-to-date config.
- The imports of packit are simplier.
- The preparation of SRPM build has been refactored including new exceptions.

# 0.7.1

## Minor

- The "Developer Certificate of Origin" was added to the git repository.

## Fixes

- Packit will determine `upstream_project_url` from git remote if not specified in the config.

# 0.7.0

See our [website](https://packit.dev) for up-to-date documentation on how to
use the new features described below.

## Deprecation changes

- Rename `upstream_project_name` option to `upstream_package_name`.
  - The old one is now deprecated and will be ignored in the future.

## Features

- Packit is now able to be used from a distgit repository.
  - You need to specify `upstream_project_url` to make it work.
- New option (`upstream_tag_template`) was added to the configuration file to
  support more versioning schemes.
- You can now use `Source` and `Source0` macros to define upstream sources.
- The configuration of the authentication was reworked: it nested under
  `authentication` key.
  - The scheme now supports multiple git services.

## Fixes

- Packit now verifies the output of the `create-archive` action.

# 0.6.1

This patch release contains only few bug-fixes on top of 0.6.0.

# 0.6.0

We keep our documentation up to date: https://packit.dev/docs - you can learn
how to use all the latest features.

## Breaking changes

- `pagure_fork_token` is no longer needed given a change which happened in
  pagure (src.fedoraproject.org); [Pierre](https://pagure.io/user/pingou)
  rocks!
- New COPR projects created by packit are no longer listed in the COPR
  dashboard and are set to be deleted after 180 days upon being created.

## Features

- There is a new command `push-updates` to mark bodhi updates for stable.
- Packit now sets description and instructions for newly created COPR projects.
- There is a new config option to set ID of a spec file Source which packit
  should operate on (defaults to 0). Packit now also updates the `%[auto]setup`
  macro in `%prep` so that the generated archive is correctly unpacked - this
  behavior matches what tito does.
- There is a new action `fix-spec` which by default sets Source0, %version and
  %setup macros in spec file - you can override it with your own
  implementation. [Documentation](https://packit.dev/docs/actions)
- Packit now sets certain environment variables during `fix-spec` and
  `create-archive` actions. You can read more about this in the documentation
  for actions.

## Fixes

- Packit can be again installed as an RPM: it correctly depends on koji client
  library now.
- If an error happens in a section while doing `status`, the section is now
  skipped and rest of the information is printed.
- Packit is able to handle URLs to git repo if they end with a slash.

# 0.5.1

## Breaking changes

- Command `version` no longer exists and is now replaced with a `--version`
  option. (thanks to @FrNecas)

## Fixes

- Fix creation of SRPMs - they can be rebuilt now properly.
- Don't update %changelog if it's not present in the spec file.
- Koji builds are now obtained using koji, not bodhi, in `status` command which
  should yield more consistent results.
- Comments in generated .packit.yaml (using `generate` command) should be now
  more accurate.
- Command `sync-from-downstream` no longer creates a branch when using option
  `--no-pr`.
- Building in copr now yields an URL to frontend instead of a link to log files.
- `status` command now displays one update per stable Fedora release.

## Minor

- We are using softwarefactory.io Zuul now instead of Centos CI jenkins.
- CONTRIBUTING.md file is now fully up to date when it comes to CI testing.
- Updates to our testing scripts.

# 0.5.0

All the documentation was moved to our site: https://packit.dev/docs

## Features

- If you set up `fas_username` in your config, packit will perform kinit before
  doing an authenticated dist-git clone.
- You can now specify a koji target when building in koji using the `build`
  command.
- There is a new command `copr-build` which enables you to submit builds into
  Fedora COPR build system.
- The config file now has a new attribute called `create_pr` which tells packit
  whether it should create pull requests in dist-git or push directly.
- `build` command now waits for the build to finish and has a `--nowait`.
- Packit now supports the most popular archive formats, not just .tar.gz
  (thanks to @FrNecas for contributing this feature)
- Command `propose-update` can now push directly to dist-git. This can be
  controlled via a CLI option `--nopr` or in a config using `create_pr` value.
- When doing a `propose-update`, packit no longer does a 1:1 copy, instead it
  copies everything from the upstream spec except for %changelog and then
  performs `rpmdev-bumpspec`.

## Fixes

- SRPMs are now being correctly created from source-git repos.
- Packit is now able to clone a dist-git repo using authentication (`fedpkg clone`) and push to it afterwards.
- `packit status` now displays also a latest rawhide koji build.
- The command `propose-update` does no longer fail when looking for an upstream
  archive.
- Packit no longer discards changes in the local git repo if it's dirty.

## Minor

- Several improvements to text printed by packit.
- We are now using Zuul for testing and have multiple jobs set up to verify
  packit works against different versions of dependant software.

# 0.4.2

- Packit now uses [Sandcastle](https://github.com/packit-service/sandcastle) to run untrusted commands in a sandbox.
- Service code has been moved to separate [repo](https://github.com/packit-service/packit-service).
- [Actions](https://github.com/packit-service/packit/blob/master/docs/actions.md) [now support](https://github.com/packit-service/packit/pull/363) more commands per action.
- Lots of code, documentation and tests fixes.

# 0.4.1

- Patch release with few fixes/minor changes.

# 0.4.0

## Features

- Packit service now submits builds in [copr](https://copr.fedorainfracloud.org) and once they're done it adds a GitHub status and comment with instructions how to install the builds.
- Packit service is now configurable via [jobs](https://packit.dev/docs/configuration/#packit-service-jobs) defined in configuration file.
- Packit is now able to check GPG signatures of the upstream commits against configured fingerprints.
- [CLI] `srpm` command now works also with [Source-git](https://packit.dev/source-git/).
- Fedmsg parsing has been unified into a single `listen-to-fedmsg` command.
- Packit service: Github webhook now reacts to ping event and validates payload signature.

## Fixes

- More source-git related changes have been applied.
- Few tracebacks when using CLI have been fixed.
- RPM package now really contains generated man pages.

## Minor

- Packit service runs on httpd server.
- [CLI] `status` command now access remote APIs asynchronously in parallel, which should speed up the execution.
- CLI now has `--dry-run` option to not perform any remote changes (pull requests or comments).
- Repository now includes Dockerfile and we by default use Docker instead of ansible-bender to build container image.
- Repository now includes Vagranfile.
- List of on-boarded projects has been moved to [README.md](https://github.com/packit-service/packit/blob/master/README.md#already-on-boarded)

# 0.3.0

We have a brand new website: https://packit.dev/!
[packit.dev repo](https://github.com/packit-service/packit.dev) contains source content for [Hugo website engine](https://gohugo.io).

## Features

- Packit supports [Source-git](https://packit.dev/source-git/).
- You can now specify your own actions to replace default packit behavior.
- Packit supports pagure.io-based upstream projects.
- Packit {propose-update, sync-from-downstream} supports copying directories.
- A new `status` command to display useful upstream/downstream info.
- You can now have a config file for packit in your home directory(`~/.config/packit.yaml`).
- Packit installed from an RPM now has manpages.

## Fixes

- Downstream pull requests titles now have correct version numbers.
- `sync-from-downstream` command constructs a PR correctly when origin is a fork.

## Minor

- Improved documentation.
- Code refactoring.
- Added MIT license notice into python files.
- CI shows code coverage and runs linters/checkers defined in pre-commit config file.
- We've started work on packit service by implementing a handler for a Github
  webhook. More to come in the next cycle!
- Packit is able to authenticate as a GitHub App.

# 0.2.0

## Breaking Changes

- We have renamed two variables in our configuration file:
  - `package_name` → `downstream_package_name`
  - `upstream_name` → `upstream_project_name`

## Features

- You can now use packit to sync files from your dist-git repo into upstream
  (mainly to keep spec files in sync). `sync-from-downstream` is the command.
- An SRPM can be created out of the current content in your upstream repository
  — please check out the `srpm` command.
- Packit is able to create bodhi updates using the `create-update` command.
- You can ask packit to build the latest content of your dist-git
  repository in koji: the command is `build`.
- We have added `--force-new-sources` option to propose-update update command
  to bypass our caching optimization.
- `propose-update` command now has option `--local-content` which disables
  checking out the tag with the upstream release. This is useful if you forget
  to bump your spec file when doing a release.
- You are now able to pick a specific upstream release version in
  `propose-update` command.

## Fixes

- Packit checks if the upstream tarball is already present in the lookaside
  cache so it's not uploaded twice. We have fixed a behavior when the upload
  part was skipped while having old tarball specified in dist-git. Packit now
  does the right thing - checks if sources file has the correct tarball
  referenced.
- We have updated several error messages which were coming from GitPython and
  it was not clear what's wrong.

## Minor

- We have added CONTRIBUTING.md to ease contribution to packit. All your
  patches are welcome!
- We are now using black, flake8 and mypy to improve code quality.
- We have moved some info from README to dedicated doc. Also, all the
  documentation should be up to date.

# 0.1.0

The first official release of packit!

## Features

- `packit propose-update` brings a new upstream release into Fedora rawhide.
  For more info, please [check out the documentation](https://packit.dev/docs/cli/propose-update/).

- `packit watch-releases` listens to github events for new upstream releases.
  If an upstream project uses packit, it would bring the upstream release into
  Fedora, the same way as `packit propose-update`. Please make sure that your
  upstream project is set up using
  [github2fedmsg](https://apps.fedoraproject.org/github2fedmsg/).
