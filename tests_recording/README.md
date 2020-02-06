# Recording testsuite

This testsuite uses [Requre project](https://github.com/packit-service/requre)
to store data from test using real credenials and communication with real
servers, etc.

## Add new substitutions if missing

If you find, that you should replace more parts that are covered now.
Please add your code to [replacements](https://github.com/packit-service/packit/tree/master/tests/testsuite_recording/replacements.py)

## Regenerate data for tests

There were troubles that different version of `ogr` or `rebasehelper`
contained different behaviour, so that we had to generate these response
files with various versions of these tools.

You can do it on your computer as the easiest way, becauase you have
all credentials there eg:

- github token
- pagure token
- kerberos tickets
- ssh keys

### Command to run

Ensure to remove files and directories for tests what you would like to
regenerate.

```
PAGURE_TOKEN=your_token GITHUB_TOKEN=your_token pytest-3 -v tests/testsuite_recording
```

#### Matrix

Install `requre` from git master branch

- first round
  - `ogr` - from master branch
  - `rebasehelper` - version `0.19.0` and above
- second round for test `for test_version_change_exception`
  - `ogr` - from master branch
  - `rebasehelper` - `0.17.1`
- third round
  - `ogr` - released (rpm or pypi)
  - `rebasehelper` - `0.19.0` and above
