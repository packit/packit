"""
This script is meant to accept source git repo with a branch as an input and build it in Fedora

It is expected to do this:

1. clone the repo
2. create archive out of the sources
3. create SRPM
4. submit the SRPM to koji
5. wait for the build to finish
6. update github status to reflect the result of the build
"""
import sys

from sourcegit.transformator import Transformator


def usage():
    print(f"Usage: {sys.argv[0]} GIT_REPO UPSTREAM_NAME PACKAGE_NAME VERSION")
    return -1


def main():
    try:
        repo_url = sys.argv[1]
        upstream_name = sys.argv[2]
        package_name = sys.argv[3]
        version = sys.argv[4]
    except IndexError:
        return usage()

    t = Transformator(url=repo_url,
                      upstream_name=upstream_name,
                      package_name=package_name,
                      version=version)

    try:
        t.create_srpm()
    finally:
        t.clean()

    return 0


if __name__ == '__main__':
    sys.exit(main())
