# source-git

This project provides tooling and automation to integrate upstream open source
projects into Fedora operating system.


## What and why?

 * Our intent is to bring downstream and upstream communities closer: provide
   feedback from downstream to upstream. (e.g. *"Hello \<upstream project Y>,
   your newest release doesn't work in Fedora rawhide, it breaks \<Z>, here is
   a link to logs."*)

 * One of the implications is that it's trivial to propose changes back to
   upstream or cherry-pick fixes from upstream to downstream.

 * We expect that stability will increases: only merge, build and compose
   components which integrate well with the rest of the operating system. The
   biggest impact of such behavior will be on Fedora rawhide and when working
   on a new release.

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

 * Automatically pull and validate new upstream releases. This can be a trivial
   thing to do, why should maintainers waste their times on work which can be
   automated.


## Current status

Right now we are aiming for a proof of concept. The work is being tracked [in
this milestone](https://github.com/user-cont/source-git/milestone/1). Once it's
done, we'll create a demo and present it at [DevConf.cz](https://devconf.cz/)

The talk: [Auto-maintain your Package](https://devconfcz2019.sched.com/event/Jch1/auto-maintain-your-package)  
Time: Friday, January 25 • 4:00pm - 4:25pm  
Location: E112  


## Plans

 * Validate proposed changes
   * This means that a change is built and tested in downstream, and results
     are reported back to the pull request.

 * Synchronize changes downstream
   * Once a change is merged in a source git repo, it can be synchronized
     downstream — either directly or as a pull request on pagure.

 * Automatically pull new upstream releases.

 * Automate creation of source git repos.
   * Take a dist-git repo as an input and create a source git repo (e.g.
     [rpms/python-docker](https://src.fedoraproject.org/rpms/python-docker) →
     [TomasTomecek/docker-py-source-git](https://github.com/TomasTomecek/docker-py-source-git))

 * Enable local development in source git:
   * Some of the changes described above make it hard to perform a build
     locally. We want to preserve such workflow where maintainers verify
     locally that they changes work before pushing them out.

 * Support other git forges: pagure.io, gitlab.


## Usage

The software is far from being even an alpha quality. Most of the values and
configuration is hard-coded inside the scripts. Once we prove this project,
we'll start working on configuration and user experience. You've been warned.

There is a makefile in this repository which can be used to build the container
images and run them locally with podman.

Before that, you should create a file secrets.yaml and store your github and
[pagure API tokens](https://src.fedoraproject.org/settings#nav-api-tab) in
there. This file is then used during deployment as a source for ansible
variables which are utilized by the containers:
```yaml
$ cat ./secrets.yaml
github_token: 123456

# This token is needed to access data in pagure.
# This is meant to be an API token of your user
# https://src.fedoraproject.org/settings#nav-api-tab
pagure_user_token: 456789

# We need this token to be able to comment on a pagure pull request.
# If you don't have commit access to the package, you should ask maintainer of
# the package to generate a token for the specific dist-git repository.
# https://src.fedoraproject.org/rpms/<package>/settings#apikeys-tab
pagure_package_token: ABCDEF

# This token is needed to create a pull request
# https://src.fedoraproject.org/fork/<user>/rpms/<package>/settings#apikeys-tab
pagure_fork_token: QWERTY
```

The next thing you need, in order for the tooling to be able to push to your fork in Fedora dist-git, SSH keys.

Please place two files to the root of this repo:
 * bigger-secret — public key
 * biggest-secret — private key

Both of them are in .gitignore so they will not land in git.


Let's build and run now:
```
$ make build
$ make run-local
```


## Resources

 * An excellent document by Colin Walters which describes a modern way of
   developing a distribution:
   * https://github.com/projectatomic/rpmdistro-gitoverlay/blob/master/doc/reworking-fedora-releng.md
