[![Build Status](https://zuul-ci.org/gated.svg)](https://softwarefactory-project.io/zuul/t/local/builds?project=packit-service/packit)

![Packit](design/export/logo-extended.png)

## Elevator pitch

Packit is a CLI tool that helps developers auto-package upstream projects
into Fedora operating system.
You can use packit to continously build your upstream project in Fedora.
With packit you can create SRPMs, open pull requests in dist-git, submit koji builds and even
create bodhi updates, effectively replacing the whole Fedora packaging workflow.

## Plan and current status

We are working on two things now:

1.  Packit as a tool - a standalone CLI tool which you can install from Fedora
    repositories and use easily.
2.  Packit service - A service offering built on top of packit tool. Our
    expectation is that you would add packit service into your Github
    repository and it would start handling things automatically: opening pull
    requests on dist-git, building packages, creating updates, ...

For the run-down of the planned work, please see the task-list below.

- [ ] E2E workflow for getting upstream releases into Fedora using packit CLI.
  - [x] Bring new upstream releases into Fedora rawhide as dist-git pull
        requests. ([propose-update](https://packit.dev/docs/cli/propose-update/) command included in 0.1.0 release)
  - [x] Build the change once it's merged. #137
  - [x] Send new downstream changes back to upstream. (so the spec files are in
        sync) #145
  - [x] Packit can create bodhi updates. #139
  - [x] Ability to propose updates also to stable releases of Fedora.
  - [x] Create SRPMs from the upstream repository
  - [x] Build RPMs in COPR and integrate the results into Github.
- [ ] source-git
  - [x] Packit can create a SRPM from a source-git repo.
  - [ ] You can release to rawhide from source-git using packit.
  - [ ] Packit can create a source-git repository.
  - [ ] Packit helps developers with their source-git repositories.
- [x] Packit as a service
  - [x] Packit reacts to Github webhooks.
  - [x] Have a Github app for packit.
    - [x] Github app is on Marketplace.
  - [x] Packit service is deployed and usable by anyone.

## Workflows covered by packit

This list contains workflows covered by packit tool and links to the documentation.

- [Update Fedora dist-git with an upstream release.](https://packit.dev/docs/cli/propose-update/)
- [Build content of a Fedora dist-git branch in koji.](https://packit.dev/docs/cli/build/)
- [Create a bodhi update.](https://packit.dev/docs/cli/create-bodhi-update/)
- [Create a SRPM from the current content in the upstream repository.](https://packit.dev/docs/cli/srpm/)
- [Sync content of the Fedora dist-git repo into the upstream repository.](https://packit.dev/docs/cli/sync-from-downstream/)

## Configuration

Configuration file for packit is described [here](http://packit.dev/docs/configuration/).

TL;DR

```yaml
specfile_path: packit.spec
synced_files:
  - packit.spec
upstream_package_name: packitos
downstream_package_name: packit
```

## User configuration file

User configuration file for packit is described [here](http://packit.dev/docs/configuration/#user-configuration-file).

## Requirements

Packit is written in python 3 and is supported only on 3.6 and later.

When packit interacts with dist-git, it uses `fedpkg`, we suggest installing it:

```bash
sudo dnf install -y fedpkg
```

## Installation

On Fedora:

```
$ dnf install packit
```

You can also use our [`packit-releases` Copr repository](https://copr.fedorainfracloud.org/coprs/packit/packit-releases/)
(contains also released versions of [OGR](https://github.com/packit-service/ogr)):

```
$ dnf copr enable packit/packit-releases
$ dnf install packit
```

Or from PyPI:

```
$ pip3 install --user packitos
```

(packit project on PyPI is NOT this packit project)

You can also install packit from `master` branch, if you are brave enough:

You can use our [`packit-master` Copr repository](https://copr.fedorainfracloud.org/coprs/packit/packit-master/)
(contains `master` version of [OGR](https://github.com/packit-service/ogr)):

```
$ dnf copr enable packit/packit-master
$ dnf install packit
```

Or

```
$ pip3 install --user git+https://github.com/packit-service/packit.git
```

### Run from git directly:

You don't need need to install packit to try it out. You can run it directly
from git (if you have all the dependencies installed):

```
$ python3 -m packit.cli.packit_base --help
Usage: packit_base.py [OPTIONS] COMMAND [ARGS]...

Options:
  -d, --debug
  -h, --help         Show this message and exit.
...
```

## Who is interested

- Identity team (@pvoborni)
- Plumbers - Source Git (@msekletar @lnykryn)
- shells (@siteshwar)
- python-operator-courier (Ralph Bean)
- @thrix
- youtube-dl (Till Mass)
- [greenboot](https://github.com/LorbusChris/greenboot/) (@LorbusChris)
- ABRT
- OSBS (atomic-reactor, osbs-client, koji-containerbuild) (@cverna)
- CoreOS (starting with rpm-ostree, ignition, and ostree) (@jlebon)
- cockpit (@martinpitt)
- iptables (@jsynacek)

For the up to date list of projects which are using packit, [click here](https://github.com/packit-service/research/blob/master/onboard/status.md).

## Logo design

Created by `Marián Mrva` - [@surfer19](https://github.com/surfer19)
