# How to source-git?

This is a practical introduction to source-git using a real example.

If you are interested in the theory behind source-git, please read [the
specification](/docs/source-git.md).


## Let's create a source-git repo

I choose systemd from Fedora 29 for this example.


### What do we need?

3 things:

1. Systemd upstream repo.
2. Fedora 29 dist-git repo of systemd.
3. New local git repo.

Let's set all of this up. We'll start with an empty git repository:
```
$ mkdir systemd-source-git
$ cd systemd-source-git
$ git init .
Initialized empty Git repository in /home/tt/t/systemd-source-git/.git/
```

We'll add fedora and upstream remotes, and then we'll fetch them:
```
$ git remote add upstream https://github.com/systemd/systemd.git
$ git remote add fedora ssh://ttomecek@pkgs.fedoraproject.org/rpms/systemd.git
$ git fetch -q upstream
$ git fetch -q fedora
```

Systemd also has a dedicated repository with backports to the older releases.
This is how systemd is packaged in Fedora.
```
$ git remote add upstream-stable https://github.com/systemd/systemd-stable.git
$ git fetch -q upstream-stable
```

### We can start now

Usually you would try to figure which upstream release is used so that you know
what to choose for the base. But systemd in Fedora is not using the pristine
upstream archives.

When we open the Fedora 29 systemd spec file, we can see that upstream uses
commit hash `8bca4621fc003a148c70248c55aa877dfe61fd3f` for the upstream tarball
from the systemd-stable repo. We'll start a new git branch in our repo named
`239-sg` (sg as source-git):
```
$ git checkout -B 239-sg 8bca4621fc003a148c70248c55aa877dfe61fd3f
Switched to a new branch '239-sg'
```

Right now we have the upstream history which lead to the 239 release.
Alternatively we could just unpack the upstream tarball and have the history in
a single commit.

In this case, the upstream history is not marked in a any way, so let's tag it:
```
$ git tag upstream-239 HEAD
```
Packit will be able to distinguish between additional source-git
content and upstream history.

We can start layering downstream content on top.


### Layering downstream content on top of upstream

Let's get files from the `fedora/f29` branch.
```
$ git checkout fedora/f29 -- .
$ git status
On branch 239-sg
Changes to be committed:
  (use "git reset HEAD <file>..." to unstage)

        modified:   .gitignore
        new file:   0001-Revert-journald-periodically-drop-cache-for-all-dead.patch
        new file:   0998-resolved-create-etc-resolv.conf-symlink-at-runtime.patch
        new file:   20-grubby.install
        new file:   20-yama-ptrace.conf
        new file:   inittab
        new file:   purge-nobody-user
        new file:   sources
        new file:   split-files.py
        new file:   sysctl.conf.README
        new file:   systemd-journal-gatewayd.xml
        new file:   systemd-journal-remote.xml
        new file:   systemd-udev-trigger-no-reload.conf
        new file:   systemd-user
        new file:   systemd.spec
        new file:   triggers.systemd
        new file:   yum-protect-systemd.conf
```

We have a bunch of new files from f29 branch in the root. We'll move them now
to the `fedora/` directory:
```
$ mkdir fedora
$ mv $(git diff --name-only --cached) fedora/
```

and we should also clean our working tree:
```
$ git reset HEAD .
Unstaged changes after reset:
M       .gitignore

$ git checkout .gitignore
```

...and commit the fedora content now:
```
$ git add fedora
```

We don't want to commit those two patch files:
```
$ git reset HEAD fedora/0001-Revert-journald-periodically-drop-cache-for-all-dead.patch fedora/0998-resolved-create-etc-resolv.conf-symlink-at-runtime.patch
```

We can now commit the files in `fedora/` directory:
```
$ git commit -m 'add fedora packaging'
[239-sg 20548da6d9] add fedora packaging
 15 files changed, 2901 insertions(+)
 create mode 100644 fedora/.gitignore
 create mode 100755 fedora/20-grubby.install
 create mode 100644 fedora/20-yama-ptrace.conf
 create mode 100644 fedora/inittab
 create mode 100755 fedora/purge-nobody-user
 create mode 100644 fedora/sources
 create mode 100644 fedora/split-files.py
 create mode 100644 fedora/sysctl.conf.README
 create mode 100644 fedora/systemd-journal-gatewayd.xml
 create mode 100644 fedora/systemd-journal-remote.xml
 create mode 100644 fedora/systemd-udev-trigger-no-reload.conf
 create mode 100644 fedora/systemd-user
 create mode 100644 fedora/systemd.spec
 create mode 100644 fedora/triggers.systemd
 create mode 100644 fedora/yum-protect-systemd.conf
```


### Applying downstream patches
We are getting to the core of source-git: we work with code in it, not with
patches. Hence we need to apply the downstream patches:

```
$ git am fedora/0001-Revert-journald-periodically-drop-cache-for-all-dead.patch
Applying: Revert "journald: periodically drop cache for all dead PIDs"

$ git am fedora/0998-resolved-create-etc-resolv.conf-symlink-at-runtime.patch
Applying: resolved: create /etc/resolv.conf symlink at runtime

$ git log --oneline| head -n 2
bcc2c8a292 resolved: create /etc/resolv.conf symlink at runtime
1d39b39df9 Revert "journald: periodically drop cache for all dead PIDs"
```

And that's it, this is our source-git repo! You can check it out over
[here](https://github.com/packit-service/systemd-source-git).

Once we finish source-git related code in packit, you'd be able then to work
exclusively in source-git, getting results from tests and other testing systems
directly on pull requests.


## Wrap up
As you can see, it is a lot of work to create the source-git repo. We are
planning on automating it — creating a dedicated command in packit.

We also have a bunch of packit code related to source-git already done, but the
overall experience is not done end-to-end.
