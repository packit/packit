# Pack It! [![Build Status](https://zuul-ci.org/gated.svg)](https://softwarefactory-project.io/zuul/t/local/builds?project=packit-service/packit)

## Elevator pitch

Packit is a CLI tool that helps developers auto-package upstream projects
into Fedora operating system.
You can use packit to continously build your upstream project in Fedora.
With packit you can create SRPMs, open pull requests in dist-git, submit koji builds and even
create bodhi updates, effectively replacing the whole Fedora packaging workflow.

## Plan and current status

We are working on two things now:
 1. Packit as a tool - a standalone CLI tool which you can install from Fedora
    repositories and use easily.
 2. Packit service - A service offering built on top of packit tool. Our
    expectation is that you would add packit service into your Github
    repository and it would start handling things automatically: opening pull
    requests on dist-git, building packages, creating updates, ...

For the run-down of the planned work, please see the task-list below.


* [ ] E2E workflow for getting upstream releases into Fedora using packit CLI.
  * [x] Bring new upstream releases into Fedora rawhide as dist-git pull
        requests. ([propose-update](https://packit.dev/docs/cli/propose-update/) command included in 0.1.0 release)
  * [x] Build the change once it's merged. #137
  * [x] Send new downstream changes back to upstream. (so the spec files are in
        sync) #145
  * [x] Packit can create bodhi updates. #139
  * [x] Ability to propose updates also to stable releases of Fedora.
  * [x] Create SRPMs from the upstream repository
  * [x] Build RPMs in COPR and integrate the results into Github.
* [ ] source-git
  * [x] Packit can create a SRPM from a source-git repo.
  * [ ] You can release to rawhide from source-git using packit.
  * [ ] Packit can create a source-git repository.
  * [ ] Packit helps developers with their source-git repositories.
* [ ] Packit as a service
  * [x] Packit reacts to Github webhooks.
  * [x] Have a Github app for packit.
    * [ ] Github app is on Marketplace.
  * [ ] Packit service is deployed and usable by anyone.


## Workflows covered by packit

This list contains workflows covered by packit tool and links to the documentation.

* [Update Fedora dist-git with an upstream release.](https://packit.dev/docs/cli/propose-update/)
* [Build content of a Fedora dist-git branch in koji.](https://packit.dev/docs/cli/build/)
* [Create a bodhi update.](https://packit.dev/docs/cli/create-bodhi-update/)
* [Create a SRPM from the current content in the upstream repository.](https://packit.dev/docs/cli/srpm/)
* [Sync content of the Fedora dist-git repo into the upstream repository.](https://packit.dev/docs/cli/sync-from-downstream/)


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


## Requirements

Packit is written in python 3 and is supported only on 3.6 and later.

When packit interacts with dist-git, it uses `fedpkg`, we suggest installing it:

```bash
sudo dnf install -y fedpkg
```

## Installation

On Fedora:

```
$ dnf install --enablerepo=updates-testing packit
```

Or

```
$ pip3 install --user packitos
```

(packit project on PyPI is NOT this packit project)

You can also install packit from master branch, if you are brave enough:

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

## Already on-boarded

 Package name      | Contacts                  | Link to packit configuration file
-------------------|---------------------------|----------------------------------------------------------------------
 rebase-helper     | @nforro                   | [.packit.yaml](https://github.com/rebase-helper/rebase-helper/blob/master/.packit.yml)
 pykickstart       | @dcantrell @larskarlitski | [packit.yaml](https://github.com/dcantrell/pykickstart/blob/master/packit.yaml)
 packit            |                           | [.packit.yaml](https://github.com/packit-service/packit/blob/master/.packit.yaml)
 colin             |                           | [.packit.yaml](https://github.com/user-cont/colin/blob/master/.packit.yaml)
 conu              |                           | [.packit.yaml](https://github.com/user-cont/conu/blob/master/.packit.yaml)
 sen               | @TomasTomecek             | [.packit.yaml](https://github.com/TomasTomecek/sen/blob/master/.packit.yaml)
 ogr               | @lachmanfrantisek         | [.packit.yaml](https://github.com/packit-service/ogr/blob/master/.packit.yaml)
 rear              | @gdha                     | [PR2145](https://github.com/rear/rear/pull/2145)

## Who is interested

* Identity team (@pvoborni)
* Plumbers - Source Git (@msekletar @lnykryn)
* shells (@siteshwar)
* python-operator-courier (Ralph Bean)
* @thrix
* youtube-dl (Till Mass)
* [greenboot](https://github.com/LorbusChris/greenboot/) (@LorbusChris)
* ABRT
* OSBS (atomic-reactor, osbs-client, koji-containerbuild) (@cverna)
* CoreOS (starting with rpm-ostree, ignition, and ostree) (@jlebon)
* cockpit (@martinpitt)
* iptables (@jsynacek)

## Currently on-boarding

 Package name       | Contacts                  | Links (Bugzillas, PRs, etc.)
--------------------|---------------------------|----------------------------------------------------------------------
 anaconda           | @jkonecny12               | [BZ1697339](https://bugzilla.redhat.com/show_bug.cgi?id=1697339)
 [standard-test-roles](https://pagure.io/standard-test-roles)|                           | [PR325](https://pagure.io/standard-test-roles/pull-request/325)

## Resources

 * An excellent document by Colin Walters which describes a modern way of
   developing a distribution:
   * https://github.com/projectatomic/rpmdistro-gitoverlay/blob/master/doc/reworking-fedora-releng.md
