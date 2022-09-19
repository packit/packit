# Recording testsuite

This testsuite uses [Requre project](https://github.com/packit/requre)
to store data from test using real credentials and communication with real
servers, etc.

## Add new substitutions if missing

If you find, that you should replace more parts that are covered now.
Please add your code to [replacements](https://github.com/packit/packit/tree/master/tests/testsuite_recording/replacements.py)

## Regenerate data for tests

There were troubles that different version of `ogr` or `rebasehelper`
contained different behaviour, so that we had to generate these response
files with various versions of these tools.

The `unshare` command below will show tests which require network connectivity,
because those will fail:

    sudo unshare -n sudo -u $(whoami) pytest-3 -v -x tests_recording/test_status.py

You can do it on your computer as the easiest way, because you have
all credentials there eg:

- github token
- pagure token
- kerberos tickets
- ssh keys

### Command to run

- Ensure to remove files and directories for tests what you would like to regenerate.
- You have to have configs:
  - for packit: `~/.config/packit.yaml`
  - for copr: `~/.config/copr`

```
pytest-3 -v tests_recording
```

### Postprocessing

- Remove secrets from stored files as some parts are not covered by generic
  requre pre-commit hook for removing secrets, e.g. token and login for copr.
  Remove them manually or with:
  ```
  requre-patch purge --replaces ":set-cookie:str:a 'b';" --replaces "copr.v3.helpers:login:str:somelogin" --replaces "copr.v3.helpers:token:str:sometoken" tests_recording/test_data/*/*yaml
  ```
- Create symlinks for same test-files in `tests_data` that are saved with the response. Requre uses tar archives for saving file content and you can easily symlink them via requre tool:
  ```
  requre-patch create-symlinks `pwd`/tests_recording/test_data/
  ```

#### Matrix

Install `requre` from git master branch

- Current version of packit has no issues with various libraries versions.
  In case it happens, regenerate data with proper versions of libraries and
  add there keys for these versions.
- Define method `cassette_setup(cassette)` of your test class if not already defined.
  You can use something like `cassette.data_miner.key = rebasehelper.VERSION`.
  It appends a key with rebasehelper version.
  You can add as many keys as necessary.
