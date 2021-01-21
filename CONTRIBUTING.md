# Contributing Guidelines

Please follow common guidelines for our projects [here](https://github.com/packit/contributing).

## Reporting Bugs

- [List of known issues](https://github.com/packit/packit/issues) and in case you need to create a new issue, you can do so [here](https://github.com/packit/packit/issues/new).
- Getting a version of `packit`:<br>
  `rpm -q packit` or `pip3 freeze | grep packitos`

## Documentation

If you want to update documentation, create a PR against [packit.dev](https://github.com/packit/packit.dev).

## Testing

Tests are stored in [tests](/tests) directory:

- `tests/unit`
  - testing small units/parts of the code
  - strictly offline
- `tests/integration`
  - testing bigger parts of codebase (integration between multiple units, packit python API)
  - mocking with [flexmock](https://github.com/bkabrda/flexmock/) instead of using [requre](https://github.com/packit/requre)
- `tests/functional`
  - testing packit as a CLI
  - be careful what you run -- no requre, no mocking
- `tests_recording`
  - testing bigger parts of codebase (integration between multiple units, packit python API)
  - use [requre](https://github.com/packit/requre)
    for remote communication => offline in the CI
  - prefer [requre](https://github.com/packit/requre) instead of mocking

Running tests locally:

    make check_in_container

To select a subset of the whole test suite, set `TESTS_TARGET`.
For example to run only the unit tests use:

    TESTS_TARGET=tests/unit make check_in_container

Tests use pre-generated responses stored in [tests_recording/test_data/](tests_recording/test_data).
To (re-)generate response file(s):

- [add requre to test image](files/local-tests-requirements.yaml)
- remove files from [tests_recording/test_data/](tests_recording/test_data) you want to re-generate
- set tokens in your [~/.config/.packit.yaml](https://packit.dev/docs/configuration/#user-configuration-file)
- `make check_in_container_regenerate_data`
- commit changed/new files

See also [tests_recording/README.md](tests_recording/README.md)

The saving of the responses is turned on by the `RECORD_REQUESTS` environment variable.
The file, that will be used for storing, can be set by `RESPONSE_FILE` variable
or by setting the `storage_file` property of the persistent storage singleton.
This is the code used for base test class in the `setUp`:

```python
response_file = self.get_datafile_filename() # name generated from the test name
PersistentObjectStorage().storage_file = response_file
```

As a CI we use [Zuul](https://softwarefactory-project.io/zuul/t/local/builds?project=packit-service/packit) with a configuration in [.zuul.yaml](.zuul.yaml).
If you want to re-run CI/tests in a pull request, just include `recheck` in a PR comment.

### Additional configuration for development purposes

#### Copr build

For cases you'd like to trigger copr build in your copr project, you can configure it in
packit configuration of your chosen package:

```yaml
jobs:
  - job: copr_build
    trigger: pull_request
    metadata:
      targets:
        - some_targets
      # (Optional) Defaults to 'packit'
      owner: <your_fedora_username>
      # (Optional) Defaults to <github_namespace>-<github_repo>
      project: some_project_name
```

---

Thank you for your interest!
Packit team.
