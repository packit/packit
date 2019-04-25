# Contributing Guidelines

Thanks for your interest in contributing to `packit`.

The following is a set of guidelines for contributing to `packit`.
Use your best judgement, and feel free to propose changes to this document in a pull request.


## Reporting Bugs
Before creating bug reports, please check a [list of known issues](https://github.com/packit-service/packit/issues) to see
if the problem has already been reported (or fixed in a master branch).

If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/packit-service/packit/issues/new).
Be sure to include a **descriptive title and a clear description**. Ideally, please provide:
 * version of packit you are using (`rpm -q packit` or `pip3 freeze | grep packitos`)
 * the command you executed and a debug output (using option `--debug`)

If possible, add a **code sample** or an **executable test case** demonstrating the expected behavior that is not occurring.

**Note:** If you find a **Closed** issue that seems like it is the same thing that you're experiencing, open a new issue and include a link to the original issue in the body of your new one.
You can also comment on the closed issue to indicate that upstream should provide a new release with a fix.

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues.
When you are creating an enhancement issue, **use a clear and descriptive title** and **provide a clear description of the suggested enhancement** in as many details as possible.

## Guidelines for Developers

If you would like to contribute code to the `packit` project, this section is for you!

### Is this your first contribution?

Please take a few minutes to read GitHub's guide on [How to Contribute to Open Source](https://opensource.guide/how-to-contribute/).
It's a quick read, and it's a great way to introduce yourself to how things work behind the scenes in open-source projects.

### Dependencies

If you are introducing a new dependency, please make sure it's added to:
 * [setup.cfg](setup.cfg)

### Documentation

If you want to update documentation, find corresponding file in [docs](/docs) folder.

#### Changelog

When you are contributing to changelog, please follow these suggestions:

* The changelog is meant to be read by everyone. Imagine that an average user
  will read it and should understand the changes.
* Every line should be a complete sentence. Either tell what is the change that the tool is doing or describe it precisely:
  * Bad: `Use search method in label regex`
  * Good: `Packit now uses search method when...`
* And finally, with the changelogs we are essentially selling our projects:
  think about a situation that you met someone at a conference and you are
  trying to convince the person to use the project and that the changelog
  should help with that.

### Testing

Tests are stored in [tests](/tests) directory.
We use [Tox](https://pypi.org/project/tox) with configuration in [tox.ini](tox.ini).

Running tests locally:
```
make prepare-check && make check
```

Running tests in a container (currently broken, PRs are welcome):
```
make build-tests && make test-in-container
```

As a CI we use [CentOS CI](https://ci.centos.org/job/packit-pr/) with a configuration in [Jenkinsfile](Jenkinsfile).

### Makefile

#### Requirements

- [podman](https://github.com/containers/libpod)
- docker

#### Targets

Here are some important and useful targets of [Makefile](/Makefile):

Build a container image for packit service:
```
make build
```

Run [recipe-tests.yaml](recipe-tests.yaml) ansible playbook to install packages needed to run tests:
```
make prepare-check
```

Run tests locally:
```
make check
```

Start shell in a container from the image previously built with `make build`:
```
make shell
```

In a container, do basic checks to verify that packit can be distributed, installed and imported:
```
make check-pypi-packaging
```

### Additional configuration for development purposes

#### Copr build

For cases you'd like to trigger copr build in your copr project, you can configure it in
packit configuration of your chosen package:
```
jobs:
- job: copr_build
  trigger: pull_request
  metadata:
    targets:
      - some_targets
    # (Optional) Defaults to 'packit'
    owner: some_copr_project_owner
    # (Optional) Defaults to <github_namespace>-<github_repo>
    project: some_project_name
```

### How to contribute code to packit

1. Create a fork of the `packit` repository.
2. Create a new branch just for the bug/feature you are working on.
3. Once you have completed your work, create a Pull Request, ensuring that it meets the requirements listed below.

### Requirements for Pull Requests

* Please create Pull Requests against the `master` branch.
* Please make sure that your code complies with [PEP8](https://www.python.org/dev/peps/pep-0008/).
* One line should not contain more than 100 characters.
* Make sure that new code is covered by a test case (new or existing one).
* We don't like [spaghetti code](https://en.wikipedia.org/wiki/Spaghetti_code).
* The tests have to pass.

### Checkers/linters/formatters & pre-commit

To make sure our code is compliant with the above requirements, we use:
* [black code formatter](https://github.com/ambv/black)
* [Flake8 code linter](http://flake8.pycqa.org)
* [mypy static type checker](http://mypy-lang.org)

There's a [pre-commit](https://pre-commit.com) config file in [.pre-commit-config.yaml](.pre-commit-config.yaml).
To [utilize pre-commit](https://pre-commit.com/#usage), install pre-commit with `pip3 install pre-commit` and then either
* `pre-commit install` - to install pre-commit into your [git hooks](https://githooks.com). pre-commit will from now on run all the checkers/linters/formatters on every commit. If you later want to commit without running it, just run `git commit` with `-n/--no-verify`.
* Or if you want to manually run all the checkers/linters/formatters, run `pre-commit run --all-files`.

Thank you for your interest!
packit team.
