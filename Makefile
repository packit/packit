BASE_IMAGE := registry.fedoraproject.org/fedora:29
TEST_TARGET := ./tests/
PY_PACKAGE := packit
SOURCE_GIT_IMAGE := packit
PACKIT_TESTS_IMAGE := packit-tests

build: recipe.yaml
	ansible-bender build --build-volumes $(CURDIR):/src:Z -- ./recipe.yaml $(BASE_IMAGE) $(SOURCE_GIT_IMAGE)

build-tests: recipe-tests.yaml
	ansible-bender build -- ./recipe-tests.yaml $(SOURCE_GIT_IMAGE) $(PACKIT_TESTS_IMAGE)

check:
	PYTHONPATH=$(CURDIR) pytest-3 --color=yes --verbose --showlocals $(TEST_TARGET)

test-in-container:
	podman run --rm -ti -v $(CURDIR):/src:Z -w /src $(PACKIT_TESTS_IMAGE) make check

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

secrets.yaml:
	stat secrets.yaml || echo "Please create a file secrets.yaml according to instructions in README.md"

run-local: secrets.yaml
	ansible-playbook -e source_git_image=$(SOURCE_GIT_IMAGE) -e @secrets.yaml -i inventory-local -c local ./deploy.yaml
	podman logs -f watcher & podman logs -f syncer & sleep 999999

stop-local:
	podman stop syncer watcher

rm-local:
	podman rm syncer watcher
