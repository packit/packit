#!/usr/bin/python3

import setuptools

setuptools.setup(use_scm_version=True,
                 packages=setuptools.find_packages(exclude=['tests*']), )
