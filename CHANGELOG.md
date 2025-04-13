# 1.7.0

- We have implemented a set of options `osh_options` that allow you to customize OpenScanHub scans via config. (#2570)

# 1.6.0

- When using `fast_forward_merge_into`, `version_update_mask` is now correctly being taken into consideration. (#2551)
- We have introduced a new command group `config` for configuration-related commands and moved `validate-config` command under it, resulting in the new command being `packit config validate`. (#2559)

# 1.5.0

- Packit now supports `--base-nvr` option while submitting scans to OpenScanHub. The base nvr is pulled in from koji to perform a differential scan. (#2569)

# 1.4.0

- Packit CLI now submits Koji builds in parallel. (#2568)

# 1.3.0

- Cached values of OpenSUSE aliases are used for any exception coming from `opensuse_distro_aliases` to not break a code flow if there is any problem with getting the online ones. (#2548)
- A couple of other small improvements.

# 1.2.0

- Packit reloads spec file after `create-archive` to keep user changes. (#2533)

# 1.1.1

- Packit doesn't attempt to upload git-tracked remote sources (for example a [GPG keyring](https://docs.fedoraproject.org/en-US/packaging-guidelines/#_verifying_signatures)) to lookaside cache anymore when syncing release. (#2518)

# 1.1.0

- Thanks to the work of [Bryan Elee](https://github.com/rxbryan) (as part of his Google Summer of Code work) and [Dan Čermák](https://github.com/dcermak), there is a new `packit build in-obs` CLI command to trigger a build in [OBS](https://build.opensuse.org/). (#2067)

# 1.0.1

- `version_update_mask` now applies to EPEL dist-git branches in the same way it does to stable Fedora branches. (#2507)

# 1.0.0

- Job type `build` removed after deprecation, is now `copr_build`.
- Job type `production_build` removed after deprecation, is now `upstream_koji_build`.
- Key `upstream_project_name` removed after deprecation, is now `upstream_package_name`.
- Key `synced_files` removed after deprecation, is now `files_to_sync`.

# 0.106.0

- We have added a `--resultdir` option for building in mock via our CLI (`packit build in-mock`). (#2475)

# 0.105.0

- There is a new action/hook, `post-modifications`, that is executed after all modifications to the spec file are done and in case of syncing release after all remote sources are downloaded and before uploading to lookaside cache. You can use it for example to construct an additional source that depends on the primary source (that may not yet be available in other actions). (#2474)

# 0.104.1

- Packit now uses the fedora-distro-aliases library to expand Fedora aliases. This is Packit's original code being improved and properly maintained by the Copr team. For further suggestions about aliases, use github.com/rpm-software-management/fedora-distro-aliases.

# 0.104.0

- Packit configuration file can now have a placeholder top-level key `_` that is ignored when read.
  This is useful for storing yaml anchors in complex config files, e.g.:

```yaml
_:
  base-test: &base-test
    job: tests
    fmf_path: .distro
jobs:
  - <<: *base-test
    trigger: pull_request
    manual_trigger: true
  - <<: *internal-test
    trigger: commit
    use_internal_tf: true
```

(#2378)

- You can now define `with_opts` and `without_opts` in target-specific configuration of `copr_build` job to build with `--with` and `--without` rpmbuild options. (#2463)

# 0.103.0

- Packit now supports and defaults to `fast_forward_merge_into` syntax via `--dist-git-branches-mapping` in `dist-git init`. (#2456)

# 0.102.2

- Fixed passing list of resolved bugs when running `packit propose-downstream` or `packit pull-from-upstream`. (#2447)

# 0.102.1

- We have fixed an issue that was introduced during the unification of the interface for passing resolved Bugzillas / Jira tickets to the `sync-release` or `bodhi_update` jobs. (#2442)
- `packit validate-config` now checks for the existence of downstream package. (#2436)
- Packit now allows building VM images via CLI without any Copr repository specified. (#2434)

# 0.102.0

- Check for `upstream_project_url` presence in the configuration when `pull_from_upstream` job
  is configured was removed from `validate-config`, as this is no longer required. (#2423)
- `packit init` now adds working directories that are used in `packit prepare-sources`
  into the `.gitignore` file in the same directory where Packit config resides. (#2431)
- Previously, `create-update` command took `--resolve-bugzillas` option and `propose-downstream` command
  took `--resolve-bug` option. The options have been unified into `--resolve-bug` for better user experience.
  If you used `create-update` with `--resolve-bugzillas` you have to use `--resolve-bug`
  (or shorthand `-b`) now instead. (#2428)

# 0.101.1

- In the user configuration file, it's possible to set `default_parse_time_macros`, e.g. might be helpful in situations like [packit/packit-service#2514](https://github.com/packit/packit-service/issues/2514). (#2408)
- Packit now allows to configure mock bootstrap feature setup of Copr projects with a new `bootstrap` configuration option. (#2411)

# 0.101.0

- Packit now supports passing custom arguments to various static analyzers through `--csmock-args` CLI option and `csmock_args` configuration. (#2402)
- When synching a new release Packit is now able to fast forward a specified merge to a configured list of branches.
  Use the `dist_git_branches` new syntax as in this example:
  `{"rawhide": {"fast_forward_merge_into": ["f40"]}, "fedora-stable": {}}` (#2363)

# 0.100.3

- `dist-git init` command now allows `upstream-git-url` not to be specified. (#2387)

# 0.100.2

- We have improved logging of Copr errors. (#2383)
- We have dropped a dependency that was used for Bodhi and is no longer needed. (#2381)

# 0.100.1

- Dummy release to test the "build in side tags" new feature!

# 0.100.0

- `packit pull-from-upstream` now allows omitting `upstream_project_url` in the configuration in which case the interaction with the upstream repository is skipped during release syncing. (#2354)
- We have implemented a CLI support for Koji builds against CBS Koji instance. (#2267)

# 0.99.0

# 0.98.0

- Packit now updates its own, not yet merged, pull requests instead of creating new ones for new releases. (#2204)

# 0.97.3

- We have fixed a bug that caused inconsistency between the promised environment variables (from the docs) and the environment that has been actually provided. Now you should have access to `PACKIT_UPSTREAM_REPO` and `PACKIT_DOWNSTREAM_REPO`, if they have been cloned already, in the `post-upstream-clone` action. (#2327)

# 0.97.2

- We have fixed the syncing of ACLs for `propose-downtream` for CentOS Stream. (#2318)

# 0.97.1

- We have fixed the behaviour for `dist-git init` command when `upstream-git-url` argument is specified.

# 0.97.0

- Add a `scan-in-osh` subcommand in the CLI to perform a scan through OpenScanHub. By default, it performs a full scan of the packages and a differential scan can be performed through `--base-srpm` option. (#2301)
- When running `dist-git init` command from CLI, you can pass a command to specify a git URL of the project. (#2308)

# 0.96.0

- Packit will now upload to lookaside cache sources that are not specified by URLs and are present in the dist-git repo during release sync. Additionally, all the actions ran during syncing release will provide the PACKIT_PROJECT_VERSION env var. (#2297)
- We have fixed the syncing of ACLs during CentOS Stream release syncing. (#2298)

# 0.95.0

- `packit dist-git init` now allows specifying `--version-update-mask` option and also any arbitrary top-level configuration options. (#2288)
- We have fixed Packit auto-referencing Upstream Release Monitoring bug for release syncing to CentOS Stream. (#2284)

# 0.94.2

- Packit previously put the "[packit]" string as a prefix in the subject of pull-from-upstream commits. Now the prefix is no longer there - this is made unnecessary noise in autochangelog. This affects the default. Custom action can still override this behavior. (#2263)
- We have fixed a race condition that could occur when multiple `copr_build` jobs sharing a Copr project but having different targets were running at the same time. (#2274)

# 0.94.1

- `packit validate-config` now checks whether `upstream_project_url` is set if `pull_from_upstream` job is configured. (#2254)
- `Resolves` is changed to `Resolves:` for the dist-git commit since that's the correct format for CentOS Stream 9. (#2260)

# 0.94.0

- Added new configuration options `status_name_template` and `allowed_builders`.

# 0.93.0

- Packit now checks the version to propose against the version in specfile and doesn't create downgrade PRs. (#2239)

# 0.92.0

- Packit now supports `trigger: ignore` which can be used for templating by using the YAML. (#2234)
- Packit now searches for bugzilla about new release created by Upstream Release Monitoring to reference each time it syncs the release downstream. (#2229)

# 0.91.0

- We have introduced new CLI command `packit dist-git init` that initializes Packit configuration for release automation in dist-git repository. (#2225)
- `packit validate-config` now checks whether the Upstream Release Monitoring for the package is correctly configured if `pull_from_upstream` job is present in the configuration. (#2226)
- There is a new global configuration option `parse_time_macros` that allows to configure macros to be explicitly defined or undefined at spec file parse time. (#2222)

# 0.90.0

- `pull-from-upstream` and `propose-downstream` commands now have the `--sync-acls` option that enables syncing the ACLs between dits-git repo and fork. The default behaviour was, however, changed to not sync the ACLs. (#2214)
- Packit now properly handles exceptions when syncing ACLs during release syncing. (#2213)

# 0.89.0

- We have fixed a bug in handling chroot-specific configuration once the chroots themselves are updated. (#2194)

# 0.88.0

- We have fixed a bug preventing the release from being synced downstream if the changelog to be set is empty. (#2183)

# 0.87.1

- Packit now links the information related to upstream in PRs opened when syncing a release. (#2173)

# 0.87.0

- Packit now correctly sets the specfile content (e.g. changelog entry) even if it syncs the specfile from upstream the first time. (#2170)
- Packit now supports pre-release version in `propose_downstream` and `pull_from_upstream`. A spec file update might be required, see the documentation for more details. (#2149)

# 0.86.2

- Packit _0.86.1_ was not released on PyPI due to an internal bug, it should be fixed in this release.

# 0.86.1

- Packit _0.86.0_ was not released on PyPI due to an internal bug, it should be fixed in this release.

# 0.86.0

- Packit can now check, using the `update_version_mask`, that the proposed version release and the actual package release for the target dist-git branch are compatible. (#2156)
- Packit is now able to get the version from specfile even if the `Version` tag is not present in the specfile directly, but e.g. imported from another file. (#2157)
- Packit now allows `~^+` (special characters) in a tag (used for building the version string). (#2154)
- Enforce dist tag `%{?dist}` when updating release (#2106)

# 0.85.0

- Packit no longer downloads sources excluded using spec file conditions. (#2132)

# 0.84.0

- We have adjusted how we include the resolved bugzillas in the commit messages created when syncing the release downstream so that the resolved bugzillas are included in changelog when using %autochangelog. (#2126)
- Packit now properly cleans up the branch after syncing the release which should prevent unwanted files (e.g.tarballs) being committed in dist-git. (#2125)
- Packit no longer accepts `packit.json` or `.packit.json` as a configuration file name. (#2123)
- Packit now updates ACL of a dist-git fork when creating dist-git PRs to allow users and groups with commit rights to the original dist-git repo to push directly to a source branch. (#2112)
- We have fixed an issue that prevented you from running the jobs on the GitLab.com due to failing resolution of the upstream/downstream relationship for the cloned project. (#2120)
- We have fixed an issue that you could encounter when running the Packit from the CLI that caused misinterpretation of the repository to be an upstream repo instead of a downstream. (#2117)

# 0.83.0

- We have fixed an issue that prevented automated allowlisting in the Packit Service. (#2113)
- Packit now also detects resolved bugs in the default update notes (created from changelog diff) and assigns these when submitting the Bodhi updates. (#2111)
- Packit now exports `PACKIT_UPSTREAM_PACKAGE_NAME`, `PACKIT_DOWNSTREAM_PACKAGE_NAME` and `PACKIT_CONFIG_PACKAGE_NAME` also in the `changelog_entry` action. (#2103)

# 0.82.0

- You can now specify bugs resolved by an update by `-b` or `--resolve-bug` option for `propose-downstream` and `pull-from-upstream` commands. The values will be added by default to the changelog and commit message and provided in `commit-message` and `changelog-entry` actions as `PACKIT_RESOLVED_BUGS` env variable. (#2094)

# 0.81.0

- Packit now supports the `pkg_tool` option in the config (at the top-level or with specific packages when using the monorepo syntax). This option can be used for switching between `fedpkg` or `centpkg`. (#2085)
- When updating the `Version` tag during `propose_downstream` or `pull_from_upstream`, Packit now tries to update referenced macros (if any) rather than overwriting the references. (#2087)
- If you have concerns about Packit uploading new archives to lookaside cache before creating a pull request, you can newly set `upload_sources` to False to disable this. (#2086)
- We have fixed a bug that could cause duplicit PRs to be created when using the `commit-message` action. (#2080)
- Packit now supports `commit-message` action that can be used to override the default commit message produced by Packit during `propose-downstream` or `pull-from-upstream`. Please pay attention to our [documentation](https://packit.dev/docs/configuration/actions#commit-message) with regards to the usage of this action. (#2070)

# 0.80.0

- Packit CLI now provides a new command `pull-from-upstream`, offering the same functionality as `propose-downstream` but suited for usage from the dist-git repository with Packit configuration placed there. This was primarily added to help reproduce the behaviour of the service's [pull_from_upstream job](https://packit.dev/docs/configuration/downstream/pull_from_upstream). (#2063)
- Packit now exposes `PACKIT_PACKAGE_NAME`, `PACKIT_UPSTREAM_PACKAGE_NAME` and `PACKIT_DOWNSTREAM_PACKAGE_NAME` environment variables to all actions. (#2061)
- We have fixed a bug in `packit source-git init` caused by changed behaviour in a newer version of rpmbuild. (#2048)

# 0.79.1

- We have fixed a bug in getting allowed GPG keys when syncing the release for projects with Packit config
  in monorepo format in dist-git. (#2037)

# 0.79.0

- 2 new configuration options for filtering when getting latest upstream release tag were introduced: `upstream_tag_include` and `upstream_tag_exclude`. They should contain a Python regex that can be used as an argument in `re.match`. (#2030)

# 0.78.2

- Packit's license in RPM specfile is now confirmed to be SPDX compatible. (#2026)
- `source-git init --ignore-missing-autosetup` help was improved to be less confusing. (#2016) (#2017)

# 0.78.1

- Temporarily disabled test dependencies on Fedora Rawhide because of missing `python3-deepdiff`. (#2008)

# 0.78.0

- Packit now correctly reloads upstream specfile after running `pre-sync` action. (#2006)

# 0.77.0

- Packit now includes dist-git branch in the title of the PRs for `propose-downstream` and `pull-from-upstream`. (#1996)
- We have fixed an issue with `files_to_sync` filters not being applied properly. (#1977)

# 0.76.0

- Unsuccessful Image Builder requests now provide error details so you can fix the Image configuration. (#1981)
- Copr projects created by Packit will not follow the Fedora branching from now on.
  This decision has been made to lower the load on Copr from the temporary Copr projects created, mainly, for the PR builds.
  If you are releasing your packages to Copr, please use the new setting `follow_fedora_branching`.
  Already existing projects are not affected by this change and it is also not enforced with the custom Copr repositories. (#1970)

# 0.75.0

- Detection of `%autorelease` usage in dist-git spec file during `propose-downstream` and `pull-from-upstream` has been improved and Packit will always preserve it. (#1949)
- Changed build tool to hatchling and moved metadata to `pyproject.toml`. (PEP621) (#1913)
- Respect `upstream_ref` for tags that start with "a", "b", "c", "e", "n", "r", "s". This was caused by an issue with a `branches` prefix being treated as a set of letters to remove. (#1943)
- Reset `Release` field in dist-git spec file to `1` when the version in upstream spec file is not up-to-date with the release that triggered `propose_downstream`. (#1940)
- Correctly catch the logs, if any of the user actions fail during the propose-downstream. (#1939)
- `packit source-git` related commands can skip dist-git repos, where the git trailer is not found, when looking for the right dist-git dir where to work. (#1938)
- More monorepo related fixes. (#1946, #1947, #1948)

# 0.74.0

- Allow configuring tmt tests with fmf root outside of git root (#1936)
- Removed adding the "Signed-off-by" tag to commits created by Packit. (#1934)
- Packit's source_git functionality installs/loads the `_packitpatch` script in a more reliable manner that doesn't rely on deprecated setuptools functionality. (#1926)

# 0.73.0

- Packit now supports monorepo configuration in CLI (#1864)

# 0.72.0

- Packit now preserves `%autorelease` during `propose_downstream` and `pull_from_upstream`. (#1904)

# 0.71.0

- `upstream_tag_template` is now also used when looking for the latest version tag in Git. This allows upstream repositories to mix different tag-patterns in the same repository, but consider only one to tell the latest version. (#1891)

# 0.70.0

- Now packit uses the `get_current_version` action defined by the user to retrieve version before updating the specfile %setup macro (if any). (#1886)

# 0.69.0

- 'packit validate-config' now correctly checks glob-patterns in 'files_to_sync'. (#1865)
- Aliases logic was updated to account for the upcoming Fedora release (Bodhi now marks such release as `frozen`). (#1863)
- Command `packit validate-config` now provides details about errors when it cannot parse the config file. (#1861)
- Packit does fewer API calls when searching for the package configuration file in remote repositories. (#1846)
- `--update-release`/`--no-update-release` now affects only `Release`, not `Version`. (#1857)
- Packit now provides `PACKIT_PROJECT_VERSION` environment variable when running `changelog-entry` action. (#1853)

# 0.68.0

- Packit now requires bodhi in version 7.0.0 at minimum. (#1844)
- You can now use `--srpm` option with the `packit build locally` CLI command. (#1810)

# 0.67.0

- Packit now sanitizes changelog messages in order not to break spec file parsing. (#1841)

# 0.66.0

- When configuring Copr chroot (target in Packit terminology) specific configuration, make sure to specify `additional_modules` as a string containing module names separated with a comma, example: "httpd:2.4,python:4". (#1826)
- Target-specific configuration for Copr builds can now be defined and Packit will set it for the appropriate Copr chroots. (#1822)
- You can now specify `update_release: false` in the configuration to tell Packit not to change the `Version` and `Release` in the spec file. It works the same as `--no-update-release` (renamed from now deprecated `--no-bump`) in the CLI. (#1827)
- Packit now supports setting `module_hotfixes` for Copr projects. (#1829)
- All Copr projects created by Packit now default to `enable_net=False`. Our documentation stated this but it wasn't the case. This is now corrected. (#1825)

# 0.65.2

- No changes. This is a fixup release for sake of Packit deployment.

# 0.65.1

- Packit now puts the correct release number into the changelog when the `Release` tag is reset during `propose-downstream`. (#1816)

# 0.65.0

- Packit now correctly handles a race condition when it tries to create bodhi updates for builds that are not yet tagged properly. CLI exprience was also improved for this case. (#1803)
- Packit now resets the `Release` tag during `propose-downstream` if the version is updated and the `Release` tag has not explicitly been overridden in the upstream specfile. (#1801)

# 0.64.0

- `packit propose-downstream` now uploads all remote sources (those specified as URLs) and the source specified by `spec_source_id` (whether remote or not) to lookaside. Previously, only Source0 was uploaded.

Source0 is no longer treated specially, but as `spec_source_id` is `Source0` by default, Source0 is still being uploaded by default unless `spec_source_id` is overriden. (#1778)

# 0.63.1

- Packit now correctly finds SRPM when rpmbuild reports warnings when it parses the spec file. (#1772)
- When packit.yaml is present in the repo but is empty, Packit now produces a better error message instead of an internal Python exception. (#1769)

# 0.63.0

- Fixed an issue due to which the repository was never searched for a specfile if 'specfile_path' was not specified, and 'specfile_path' was always set to '<repo_name>.spec'. (#1758)
- Packit is now able to generate automatic Bodhi update notes including a changelog diff since the latest stable build of a package. (#1747)

# 0.62.0

- Fixed an issue with version and release being updated even if `--no-bump` flag was specified. Also fixed an issue when `None` appeared in release instead of a number. (#1753)

# 0.61.0

- Packit can now correctly authenticate with Bodhi 6 and therefore create Bodhi updates. 🚀 (#1746)
- Packit now requires Python 3.9 or later. (#1745)

# 0.60.0

- Propose downstream job now pushes changes even when it's not creating a new pull request. This allows updating already existing pull requests. (#1725)

# 0.59.1

- 'packit propose-downstream' is now more informative when sources cannot be downloaded. (#1698)

# 0.59.0

- Packit CLI can now submit VM images in Red Hat Image Builder.
  All build-related commands have now consistent `--wait`/`--no-wait` options. (#1666)
- No more annoying issues will be created after a successfull propose downstream. (#1693)

# 0.58.0

- Action `fix_spec_file` can change a spec file - Packit now preserves that change. (#1679)
- Packit now uses (py)rpkg instead of rebasehelper to parse `sources` files in dist-git repos and to interact with lookaside cache. (#1680)
- `prepare-sources` command now has a new `--no-create-symlinks` option (together with the opposite `--create-symlinks`), which enables copying the archive instead of symlinking. (#1682)

# 0.57.0

- BREAKING CHANGE: fixed an issue where the repo was searched for the specfile before checking if 'downstream_package_name' is set, and '<downstream_package_name>.spec' can be used as the 'specfile_path'. (#1663)

# 0.56.0

- Packit can now build RPMs in mock. For more information see https://packit.dev/docs/cli/build/mock (#1662)
- Packit now provides a more helpful error message when it hits a known issue while creating a Bodhi update: fedora-infra/bodhi#4660 (#1660)
- Packit now correctly supports `tmt_plan` and `tf_post_install_script` in the configuration. (#1659)
- RPM build commands of Packit CLI have been merged into one build subcommand, for more information see the updated documentation at https://packit.dev/docs/cli/build/. We have also introduced a new `--srpm` option to the new build subcommand that can be used to trigger local, Copr or Koji build from an already built SRPM rather than the one implicitly created by Packit. (#1611)

# 0.55.0

- Packit can now correctly create bodhi updates using the new Bodhi 6 client. (#1651)

# 0.54.0

- Packit Bash completion file is no longer needlessly executable. (#1634)
- Transition to Bodhi's new authentication mechanism is now fully complete. (#1635)

# 0.53.0

- Packit now works with Bodhi 5 and Bodhi 6 authentication mechanism. (#1629)
- Git ref name that Packit works with during `propose-downstream` is now made more obvious in logs. (#1626)
- Packit now correctly handles creation of custom archives in root while a specfile is in a subdirectory. (#1622)
- Creation of a Bodhi update will not timeout anymore as Packit is now using a more efficient way of obtaining the latest build in a release. (#1612)

# 0.52.1

- Fixed a regression where string values for the 'targets' and 'dist_git_branches' configuration keys were not accepted. (#1608)

# 0.52.0

- Packit will not raise exceptions anymore when creating an SRPM with dangling symlinks. (#1592)
- `packit validate-config` now checks the paths in the package config (path of the specfile,
  paths of the files to be synced) relative to the project path (#1596)
- The name of the temporary branch in `_packitpatch` was normalized which fixed applying the patches during `packit source-git init` (#1593)

# 0.51.0

- We have decided to deprecate `metadata` section for job configurations. All
  metadata-specific configuration values can be placed on the same level as the job
  definition. For now we are in a backward-compatible period, please move your settings
  from the `metadata` section. (#1569)
- Packit now correctly removes patches during `packit source-git init` when the
  preamble does not contain blank lines. (#1582)
- `packit source-git` commands learnt to replace Git-trailers in commit
  messages if they already exist. (#1577)
- Packit now supports `--release-suffix` parameter in all of the related CLI
  commands. Also we have added a support for the `release_suffix` option from
  configuration to the CLI. With regards to that we have introduced a new CLI
  switch `--default-release-suffix` that allows you to override the configuration
  option to Packit-generated default option that ensures correct NVR ordering
  of the RPMs. (#1586)

# 0.50.0

- When initializing source-git repos, the author of downstream commits created from patch files which are not in a git-am format is set to the original author of the patch-file in dist-git, instead of using the locally configured Git author. (#1575)
- Packit now supports `release_suffix` configuration option that allows you to override the long release string provided by Packit that is used to ensure correct ordering and uniqueness of RPMs built in Copr. (#1568)
- From the security perspective, we have to decided to disable the `create_pr` option for our service, from now on Packit will unconditionally create PRs when running `propose-downstream`.
  We have also updated the `propose-downstream` CLI such that it is possible to use `create_pr` from configuration or override it via `--pr`/`--no-pr` options. (#1563)
- The `source-git update-*` commands now check whether the target repository is pristine and in case not raise an error. (#1562)

# 0.49.0

- A new configuration option `downstream_branch_name` has been added,
  which is meant to be used in source-git projects and allow users
  to customize the name of the branch in dist-git which corresponds
  to the current source-git branch. (#1555)
- Introduced two new build and test target aliases: `fedora-latest-stable`
  resolves to the latest stable Fedora Linux release, while `fedora-branched`
  resolves to all branched releases (all Fedora Linux release, except `rawhide`). (#1546)
- When using `post_upstream_clone` to generate your spec-file,
  Packit now correctly checkouts the release before the action is run. (#1542)

# 0.48.0

- `packit source-git update-dist-git` and `packit source-git update-source-git` now check the synchronization of source-git and dist-git repositories prior to doing the update. If the update can't be done, for example, because the histories have diverged, the command provides instructions on how to synchronize the repositories. A `--force` option is available to try to update the destination repository anyway.
- Downstream synchronization of the Packit configuration file (aka `packit.yaml`) should be fixed. (#1532)
- Packit will no longer error out when trying to create a new Copr repository when it is already present (caused by a race condition). (#1527)
- Interactions with Bodhi should be now more reliable when creating Bodhi updates. (#1528)

# 0.47.1

- When using Packit CLI for creating Bodhi updates, you can now set `fas_username` and `fas_password`
  in your Packit user config to not be asked about that when the command is executed. (#1517)

# 0.47.0

- When specfile is being generated, and both `specfile_path` and
  `downstream_package_name` are not set, Packit now correctly resolves this
  situation and sets `specfile_path` to the name of the upstream repo suffixed
  with ".spec". (#1499)
- We are now building SRPMs for Packit's own PRs in Copr. For more info see #1490 and
  https://packit.dev/docs/configuration/#srpm_build_deps (#1490)
- All source-git-commands were updated to append a `From-source-git-commit` or `From-dist-git-commit`
  Git-trailer to the commit messages they create in dist-git or source-git, in order to
  save the hash of the commits from which these commits were created. This information
  is going to be used to tell whether a source-git repository is in sync with the
  corresponding dist-git repository. (#1488)
- Spec file and configuration file are no more automatically added to the list of files
  to sync when the `new files_to_sync` option is used. The old `synced_files` option is
  deprecated. (#1483)
- We have added a new configuration option for Copr builds `enable_net` that allows you to
  disable network access during Copr builds. It is also complemented by
  `--enable-net/--disable-net` CLI options if you use Packit locally. (#1504)

# 0.46.0

- Synchronization of default files can now be disabled using a new config
  `files_to_sync`. Key `sync_files` is now deprecated. (#1483)
- Packit now correctly handles colons in git trailer values in source-git commits. (#1478)
- Fedora 36 was added to the static list of `fedora-` aliases. (#1480)

# 0.45.0

- A new `packit source-git update-source-git` command has been introduced for
  taking new changes from dist-git (specified by a revision range) to source-git.
  These may include any changes except source code, patches and `Version` tag
  changes in the spec file. ([packit#1456](https://github.com/packit/packit/pull/1456))
- There's a new configuration option `create_sync_note` that allows you to
  disable creating of README by packit in downstream. ([packit#1465](https://github.com/packit/packit/pull/1465))
- A new option `--no-require-autosetup` for `source-git init` command has been
  introduced. Please note that source-git repositories not using `%autosetup` may
  not be properly initialized. ([packit#1470](https://github.com/packit/packit/pull/1470))

# 0.44.0

- Packit now correctly finds the release, even if you don't use the version as
  the title of the release on GitHub.
  ([packit#1437](https://github.com/packit/packit/pull/1437))
- Local branches are now named as `pr/{pr_id}` when checking out a PR, even
  when it's not being merged with the target branch. This results in the NVR
  of the build containing `pr{pr_id}` instead of `pr.changes{pr_id}`.
  ([packit#1445](https://github.com/packit/packit/pull/1445))
- A bug which caused ignoring the `--no-bump` and `--release-suffix` options
  when creating an SRPMs from source-git repositories has been fixed. Packit
  also doesn't touch the `Release` field in the specfile unless it needs to be
  changed (the macros are not expanded that way when not necessary).
  ([packit#1452](https://github.com/packit/packit/pull/1452))
- When checking if directories hold a Git-tree, Packit now also allows `.git`
  to be a file with a `gitdir` reference, not only a directory.
  ([packit#1458](https://github.com/packit/packit/pull/1458))

# 0.43.0

- A new `packit prepare-sources` command has been implemented for preparing
  sources for an SRPM build using the content of an upstream repository.
  ([packit#1424](https://github.com/packit/packit/pull/1424))
- Packit now visibly informs about an ongoing cloning process to remove
  potential confusion.
  ([packit#1431](https://github.com/packit/packit/pull/1431))
- The `upstream_package_name` config option is now checked for illegal
  characters and an error is thrown if it contains them.
  ([packit#1434](https://github.com/packit/packit/pull/1434))

# 0.42.0

- Running `post-upstream-clone` action in `propose-downstream` command was fixed.
  This solves the issue for projects that generate the specfile during this action.
- New config option `env` has been added for specifying environment variables
  used for running tests in the Testing Farm.

# 0.41.0

- Packit now supports `changelog-entry` action that is used when creating
  SRPM. The action is supposed to generate whole changelog entry (including
  the `-` at the start of the lines) and has a priority over any other way we
  modify the changelog with. (#1367)
- Fixed an issue, which raised an `UnicodeEncodingError`, when working with
  dist-git patch files with an encoding other than UTF-8. (#1406)
- Backup alias definitions now reflect the official release of Fedora Linux 35. (#1405)
- We have introduced a new configuration option `merge_pr_in_ci` that allows
  you to disable merging of PR into the base branch before creating SRPM in
  service. (#1395)
- Fixed an issue, where spec-files located in a sub-directory of upstream
  projects, were not placed in the root of the dist-git repo when proposing
  changes downstream. (#1402)

# 0.40.0

- Packit will deduce the version for SRPM from the spec file, if there are no git tags or action for acquiring current version defined. (#1388)
- We have introduced new options for generating SRPM packages: (#1396)
  - `--no-bump` that prevents changing of the release in the SRPM, which can be used for creating SRPMs on checked out tags/releases.
  - `--release-suffix` that allows you to customize the suffix after the release number, e.g. reference bugzilla or specific branch of the build.
- Deprecated configuration options `current_version_command` and `create_tarball_command` have been removed and are no longer supported. They are superseded by actions `get-current-version` and `create-archive`. (#1397)

# 0.39.0

- Bug in Packit causing issues with local build when the branch was named with prefix rpm has been fixed. (#1380)
- We have added a new option to Packit CLI when creating Bodhi updates, you can use `-b` or `--resolve-bugzillas` and specify IDs (separated by comma, e.g. `-b 1` or `-b 1,2,3`) of bugzillas that are being closed by the update. (#1383)

# 0.38.0

- `packit validate-config` was updated to check if files to be synced
  downstream are present in the upstream repo and emit a warning in case they
  are missing. (#1366)
- Patch files are read as byte streams now, in order to support having
  non-UTF-8 characters. (#1372)

# 0.37.0

- `packit source-git` init was updated to try to apply patches with `git am` first, and use `patch` only when this fails, in order to keep the commit message of Git-formatted (mbox) patch files in the source-git history. (#1358)
- Packit now provides `PACKIT_RPMSPEC_RELEASE` environment variable in actions. (#1363)

# 0.36.0

- `status` command has been refactored and now provides much cleaner output. (#1329)
- A log warning is raised if the specfile specified by the user in the config doesn't exist. (#1342)
- Packit by default locally merges checked out pull requests into target branch. Logging for checking out pull requests was improved to contain hashes and summaries of last commit on both source and target branches. (#1344)
- `source-git update-dist-git` now supports using Git trailers to define patch metadata, which will control how patches are generated and added to the spec-file. `source-git init` uses this format to capture patch metadata when setting up a source-git repo, instead of the YAML one. To maintain backwards compatibility, the YAML format is still parsed, but only if none of the patches defines metadata using Git trailers. (#1336)
- Fixed a bug that caused purging or syncing upstream changelog (when not configured) from specfile when running `propose-downstream`. New behavior preserves downstream changelog and in case there are either no entries or no %changelog section present, it is created with a new entry. (#1349)

# 0.35.0

- Propose-downstream: log when a PR already exists downstream (#1322).
- `packit init` to set spec file path in the config if it's not defined (#1313).
- Make it possible to clone packages from staging dist-git (#1306).
- Source-git: squash patches by patch name - no need to have a dedicated attribute, `squash_commits`, for that (#1309).
- Source-git: look for the config file in .distro/source-git.yaml as well (#1302).
- Source-git: change logging from error to warning when %prep is not using %(auto)setup (#1317).

# 0.34.0

- Source-git: `source-git init` was refactored, which also changed and simplified the CLI.

# 0.33.1

- Source-git: Updated the source-git format produced by `source-git init` (#1277)
- Source-git: drop support of packages not using %autosetup
- Source-git: Use --force when staging the .distro dir
- Source-git init: Do not download remote sources
- Source-git init: Raise an error if the dist-git repo is not pristine

# 0.32.0

- Command `packit generate` was removed. It has been deprecated for a while
  in favour of `packit init`. (#1269)
- Packit now explicitly requires git and rpm-build. (#1276)
- Source-git: Patch handling is more consistent. (#1263)
- Source-git: Passing changelog from source-git repo to dist-git was fixed. (#1265)
- Source-git: There is a new `source-git` subcommand, that groups source-git related
  commands `init` and `update-dist-git`. (#1273)

# 0.31.0

- Downstream package name is set when dist-git path is provided. (#1246)
- A bug with older Python present on Fedora Linux 32 and EPEL 8 is fixed. (#1240)
- There is a new `update-dist-git` subcommand that is
  an improved offline version of `propose-downstream`. (#1228)
- Source-git: Commit metadata newly includes `patch_id`. (#1252)

# 0.30.1

- Fixed a bug caused by new click release. (#1238)

# 0.30.0

- Patching: removed location_in_specfile from commit metadata. (#1229)
- Refactored and extended the synced_files mechanism. (#1211)
- Fixed a bug regarding the fedora-latest alias. (#1222)

# 0.29.0

- Source-git: add info about sources to packit.yaml when initiating a new source-git repo
  and don't commit dist-git sources from the lookaside cache. (#1208, #1216)
- Source-git: fix SRPM creation failing with duplicate Patch IDs. (#1206)
- Support git repository cache. (#1214)
- Reflect removed COPR chroots in a COPR project. (#1197)
- Deprecate current_version_command and create_tarball_command. (#1212)
- Fix crashing push-updates command. (#1170)
- Improve fmf/tmt tests configuration. (#1192)

# 0.28.0

- Remove the no-op `--dry-run` option.
- Handle `centos-stream` targets as `centos-stream-8`, in order to help with
  the name change in Copr.
- `fmf_url` and `fmf_ref` can be used in a job's `metadata` to specify an
  external repository and reference to be used to test the package.
- Introduce a `fedora-latest` alias for the latest _branched_ version of
  Fedora Linux.
- Add a top-level option `-c, --config` to specify a custom path for the
  package configuration (aka `packit.yaml`).
- Source-git: enable using CentOS Stream 9 dist-git as a source.
- Source-git: rename the subdirectory to store downstream packaging files from
  `fedora` to the more general `.distro`.
- Source-git: fix creating source-git repositories when Git is configured to
  call the default branch something other then `master`.

# 0.27.0

- (Source-git) Several improvements of history linearization.
- (Source-git) Detect identical patches in propose-downstream.
- (Source-git) Patches in spec file are added after first empty line below last Patch/Source.
- Fetch all sources defined in packit.yaml.
- New option to sync only specfile from downstream.

# 0.26.0

- Fix construction of the Koji tag for epel branches when running `packit create-update`. ([#1122](https://github.com/packit/packit/pull/1122))
- `create-update` now also shows a message about Bodhi requiring the password. ([#1127](https://github.com/packit/packit/pull/1127))
- `packit init` correctly picks up sources from CentOS and fetches specfile from CentOS dist-git. ([#1106](https://github.com/packit/packit/pull/1106))
- Fix translating of the target aliases by treating the highest pending version in Bodhi as `rawhide`. ([#1114](https://github.com/packit/packit/pull/1114))
- The format of Packit logs is unified for all log levels. ([#1119](https://github.com/packit/packit/pull/1119))
- There is a new configuration option `sources` which enables to define sources to override their URLs in specfile.
  You can read more about this in [our documentation](https://packit.dev/docs/configuration/#sources). ([#1131](https://github.com/packit/packit/pull/1131))

# 0.25.0

- `propose-downstream` command now respects requested dist-git branches. ([#1094](https://github.com/packit/packit/pull/1094))
- Improve the way how patches are added to spec file. ([#1100](https://github.com/packit/packit/pull/1100))
- `--koji-target` option of the `build` command now accepts aliases. ([#1052](https://github.com/packit/packit/pull/1052))
- `propose-downstream` on source-git repositories now always uses `--local-content`. ([#1093](https://github.com/packit/packit/pull/1093))
- Don't behave as if 'ref' would be always a branch. ([#1089](https://github.com/packit/packit/pull/1089))
- Detect a name of the default branch of a repository instead of assuming it to be `called master`. ([#1074](https://github.com/packit/packit/pull/1074))

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
