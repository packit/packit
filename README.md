# Packit [![Build Status](https://ci.centos.org/job/packit-master/badge/icon)](https://ci.centos.org/job/packit-master)

This project provides tooling and automation to integrate upstream open source
projects into Fedora operating system.


## What and why?

 * Our intent is to bring downstream and upstream communities closer: provide
   feedback from downstream to upstream. (e.g. *"Hello \<upstream project Y>,
   your newest release doesn't work in Fedora rawhide, it breaks \<Z>, here is
   a link to logs."*)

 * We want to only merge, build and compose components which integrate well
   with the rest of the operating system. The biggest impact of such behavior
   will be on Fedora rawhide and when working on a new release.

 * Automatically pull and validate new upstream releases. This can be a trivial
   thing to do, why should maintainers waste their times on work which can be
   automated.

 * Developing in dist-git is cumbersome. Editing patch files and moving
   tarballs around is not fun. Why not working with the source code itself?
   With source git, you'll have an upstream repository and the dist-git content
   stuffed in a dedicated directory.

 * Let's use modern development techniques such as pull requests, code review,
   modern git forges, automation and continuous integration. We have computers
   to do all the mundane tasks. Why we, as humans, should do such work?

 * We want dist-git to be "a database of content in a release" rather a place
   to do actual work. On the other hand, you'll still be able to interact with
   dist-git the same way. We are not taking that away. Source git is meant to
   be the modern, better alternative.

DevConf.cz ["Auto-maintain your package" talk](https://www.youtube.com/watch?v=KpF27v6K4Oc).


## Ehm, what's source-git?

Content of source-git repository is equivalent to dist-git, but uses upstream
format: source files instead of tarballs, git commits instead of patches.

You can host this repository, or the specific git branch, anywhere you want. If
you open a pull request, you will receive feedback on the changes:
* Does the package build with the changes?
* Do all the package tests pass?
* How about tests of the dependant packages?
* Are the changes good to be included in Fedora?

The goal of packit is to provide automation and tooling to interact with
source-git repositories so you don't have to touch dist-git ever again. Our
plan is to center development experience around upstream repositories and
source-git.

Upstream repositories and source-git repositories are pretty much the same
thing. Creating source-git only makes sense when the upstream does not accept
downstream spec file or adding spec file to such a project doesn't make sense.

For more info on source-git, please read [the detailed design doc](docs/source-git.md).

## Plan

* Automatically release to Fedora Rawhide (by the end of February 2019).
  * Once there is a new upstream release, create a PR in downstream pagure.
* Send new downstream changes back to upstream. (so the spec files are in sync)

* Provide feedback on upstream pull requests.
  * Run RPM builds in COPR and integrate the results into Github.


## Workflows covered by packit

* Update to latest upstream release in rawhide. [For more info please read the
  documentation](/docs/update.md)


## Current status

Work has begun on the MVP.

* [x] You can release to rawhide using packit
  * [x] Implement `propose-update` command (in master now)
* [ ] source-git
  * [ ] You can release to rawhide from source-git using packit
* [ ] Packit as a service
  * [ ] Packit reacts to Github webhooks
  * [ ] Have a github app for packit
  * [ ] Deployment


## Requirements

Packit is written in python 3 and is supported only on 3.6 and later.


## Installation

You can install packit using `pip`:

```
$ pip3 install --user git+https://github.com/packit-service/packit.git
```


## Candidates for early adoption

Please, open a PR if you want to be on the list, or just let us know.

* Identity team (@pvoborni)
* Plumbers & shells (@msekletar @lnykryn @siteshwar)
* pykickstart (@dcantrell @larskarlitski)
* python-operator-courier (Ralph Bean)
* @thrix
* youtube-dl (Till Mass)
* anaconda (@jkonecny12)
* [greenboot](https://github.com/LorbusChris/greenboot/) (@LorbusChris)


## Resources

 * An excellent document by Colin Walters which describes a modern way of
   developing a distribution:
   * https://github.com/projectatomic/rpmdistro-gitoverlay/blob/master/doc/reworking-fedora-releng.md
