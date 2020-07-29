#!/bin/bash
set -ex

PROJECT_NAME=packit
ORG=packit-service
PACKAGE_NAME=python3-$PROJECT_NAME
GITHUB=https://github.com/$ORG/$PROJECT_NAME.git

WHERETOUNPACK=$PROJECT_NAME
FIND_VERSION=`rpm -q $PACKAGE_NAME | sed -r "s/.*-$PROJECT_NAME-(.*)\.[a-zA-Z0-9_]+$/\1/"`
VERSION="${FIND_VERSION%-*}"

git clone $GITHUB $WHERETOUNPACK
(
    cd $WHERETOUNPACK
    git checkout tags/$VERSION
)
cp -rf $WHERETOUNPACK/tests tests
rm -rf $WHERETOUNPACK

# Some tests call Git commands which need an identity configured
git config --global user.name "Packit Test Suite"
git config --global user.email "test@example.com"

PYTHONPATH="$PYTHONPATH:." pytest-3 -v tests
