# source-git

This project provides tooling to integrate upstream open source projects with
Fedora operating system.

## What and why?

 * One of the intents is stability: only merge, build and compose components
   which integrate well with the rest of the operating system. The biggest
   impact will be on Fedora Rawhide and when working on a new release.

 * Developing in dist-git is cumbersome. Editing patch files and moving
   tarballs around is not fun. Why not working with the source code itself?
   With source git, you'll have an upstream repository and the dist-git content
   stuffed in a dedicated directory.

 * Automatically pull and validate new upstream releases. This can be a trivial
   thing to do, why should maintainers waste their times on work which can be
   automated.

## Plans

 * Validate proposed changes
   * This means that a change is built and tested in downstream, and results
     are reported back to the pull request.

 * Synchronize changes downstream
   * Once a change is merged in a source git repo, it can synchronized
     downstream — either directly or as a pull request on pagure.

 * Automatically pull new upstream releases.

 * Automate creation of source git repos.
   * Take a dist-git repo as an input and create a source git repo (e.g.
     [rpms/python-docker](https://src.fedoraproject.org/rpms/python-docker) → [TomasTomecek/docker-py-source-git](https://github.com/TomasTomecek/docker-py-source-git))


## Resources

https://github.com/projectatomic/rpmdistro-gitoverlay/blob/master/doc/reworking-fedora-releng.md
