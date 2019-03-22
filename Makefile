TEST_TARGET := ./tests/
PY_PACKAGE := packit
SOURCE_GIT_IMAGE := packit
PACKIT_TESTS_IMAGE := packit-tests

build: recipe.yaml
	ansible-bender build -- ./recipe.yaml

prepare-check:
	ansible-playbook -b -K -i inventory-local -c local ./recipe-tests.yaml

check:
	tox

shell:
	podman run --rm -ti -v $(CURDIR):/src:Z -w /src $(SOURCE_GIT_IMAGE) bash

check-pypi-packaging:
	podman run --rm -ti -v $(CURDIR):/src:Z -w /src $(SOURCE_GIT_IMAGE) bash -c '\
		set -x \
		&& rm -f dist/* \
		&& python3 ./setup.py sdist bdist_wheel \
		&& pip3 install dist/*.tar.gz \
		&& packit --help \
		&& pip3 show $(PY_PACKAGE) \
		&& twine check ./dist/* \
		&& python3 -c "import packit; assert packit.__version__" \
		&& pip3 show -f $(PY_PACKAGE) | ( grep test && exit 1 || :) \
		'

build-tests: recipe-tests.yaml
	ansible-bender build -- ./recipe-tests.yaml $(SOURCE_GIT_IMAGE) $(PACKIT_TESTS_IMAGE)

# FIXME: is not working ATM
test-in-container:
	podman run --rm -ti -v $(CURDIR):/src:Z -w /src $(PACKIT_TESTS_IMAGE) make check
