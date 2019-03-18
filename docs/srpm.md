# `packit srpm`

Create a SRPM of the present content in the upstream repository.

By default, packit uses `git describe --tags --match '*.*'` to create a unique
version of the snapshot and `git archive -o "{package_name}-{version}.tar.gz"
--prefix "{package_name}-{version}/" HEAD` to create a tarball with upstream
sources.

You can override the archive and version commands in [packit.yaml](configuration.md), e.g. this is
what we use in [ogr](https://github.com/packit-service/ogr/blob/master/.packit.yaml), a library which packit is using:
```yaml
create_tarball_command: ["python3", "setup.py", "sdist", "--dist-dir", "."]
current_version_command: ["python3", "setup.py", "--version"]
```


## Requirements

* Upstream project is using git.
* Packit config file placed in the upstream repository.


## Tutorial

1. [Place a config file for packit in the root of your upstream repository.](/docs/configuration.md).

2. Now we would generate a SRPM for ogr project:
   ```bash
   $ packit srpm
   Version in spec file is "0.0.3".
   SRPM: /home/tt/g/user-cont/ogr/python-ogr-0.0.4.dev11+gc9956c9.d20190318-1.fc29.src.rpm
   ```
   We can now build the package:
   ```bash
   $ rpmbuild --rebuild /home/tt/g/user-cont/ogr/python-ogr-0.0.4.dev11+gc9956c9.d20190318-1.fc29.src.rpm
   Installing /home/tt/g/user-cont/ogr/python-ogr-0.0.4.dev11+gc9956c9.d20190318-1.fc29.src.rpm
   Executing(%prep): /bin/sh -e /var/tmp/rpm-tmp.95VZ3c
   + umask 022
   + cd /home/tt/rpmbuild/BUILD
   + cd /home/tt/rpmbuild/BUILD
   + rm -rf ogr-0.0.4.dev11+gc9956c9.d20190318
   + /usr/bin/gzip -dc /home/tt/rpmbuild/SOURCES/ogr-0.0.4.dev11+gc9956c9.d20190318.tar.gz
   + /usr/bin/tar -xof -
   + STATUS=0
   ...
   Executing(%build): /bin/sh -e /var/tmp/rpm-tmp.aYyTMP
   ...
   Executing(%install): /bin/sh -e /var/tmp/rpm-tmp.fotlPv
   ...
   + exit 0
   Provides: python3-ogr = 0.0.4.dev11+gc9956c9.d20190318-1.fc29 python3.7dist(ogr) = 0.0.4.dev11+gc9956c9.d20190318 python3dist(ogr) = 0.0.4.dev11+gc9956c9.d20190318
   Requires(rpmlib): rpmlib(CompressedFileNames) <= 3.0.4-1 rpmlib(FileDigests) <= 4.6.0-1 rpmlib(PartialHardlinkSets) <= 4.0.4-1 rpmlib(PayloadFilesHavePrefix) <= 4.0-1
   Requires: python(abi) = 3.7 python3.7dist(gitpython) python3.7dist(libpagure) python3.7dist(pygithub) python3.7dist(python-gitlab)
   Checking for unpackaged file(s): /usr/lib/rpm/check-files /home/tt/rpmbuild/BUILDROOT/python-ogr-0.0.4.dev11+gc9956c9.d20190318-1.fc29.x86_64
   Wrote: /home/tt/rpmbuild/RPMS/noarch/python3-ogr-0.0.4.dev11+gc9956c9.d20190318-1.fc29.noarch.rpm
   + exit 0
   ```


## `packit srpm --help`

```
Usage: packit srpm [OPTIONS] [PATH_OR_URL]

  Create new SRPM (.src.rpm file) using content of the upstream repository.

  PATH_OR_URL argument is a local path or a URL to the upstream git
  repository, it defaults to the current working directory

Options:
  --output FILE  Write the SRPM to FILE instead of current dir.
  -h, --help     Show this message and exit.
```
