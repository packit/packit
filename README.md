# Packit

[![Build Status](https://zuul-ci.org/gated.svg)](https://softwarefactory-project.io/zuul/t/local/builds?project=packit-service/packit)
[![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

![Packit](design/export/logo-no-borders.png)

---

Packit is a CLI tool that helps developers auto-package upstream projects
into Fedora operating system.

You can use packit to continously build your upstream project in Fedora.

With packit you can create SRPMs, open pull requests in dist-git, submit koji builds and even create bodhi updates, effectively replacing the whole Fedora packaging workflow.

---

## To start using Packit

See our [documentation](https://packit.dev/docs/guide/)

## To start developing Packit

The [Contributing Guidelines](CONTRIBUTING.md) hosts all information you need to know to contribute to code and documentation, run tests and additionnal configuration.

## Workflows covered by packit

This list contains workflows covered by packit tool and links to the documentation.

- [Update Fedora dist-git with an upstream release.](https://packit.dev/docs/cli/propose-update/)
- [Build content of a Fedora dist-git branch in koji.](https://packit.dev/docs/cli/build/)
- [Create a bodhi update.](https://packit.dev/docs/cli/create-bodhi-update/)
- [Create a SRPM from the current content in the upstream repository.](https://packit.dev/docs/cli/srpm/)
- [Sync content of the Fedora dist-git repo into the upstream repository.](https://packit.dev/docs/cli/sync-from-downstream/)

## Requirements

Packit is written in python 3 and is supported only on 3.6 and later.

## Installation

For complete informations on how to start using packit, please [click here](https://packit.dev/docs/guide/#have-packit-tooling-installed-locally).

## User configuration file

User configuration file for packit is described [here](http://packit.dev/docs/configuration/#user-configuration-file).

## Who is interested

For the up to date list of projects which are using packit, [click here](https://dashboard.packit.dev/projects).

## Logo design

Created by `Marián Mrva` - [@surfer19](https://github.com/surfer19)
