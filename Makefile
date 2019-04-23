TEST_TARGET := ./tests/
PY_PACKAGE := packit
PACKIT_IMAGE := docker.io/usercont/packit-service
PACKIT_TESTS_IMAGE := packit-tests

build: recipe.yaml files/install-rpm-packages.yaml
	docker build --rm -t $(PACKIT_IMAGE) .

build-with-ab: recipe.yaml
	ansible-bender build -- ./recipe.yaml

push-to-dockerd:
	ansible-bender push docker-daemon:$(PACKIT_IMAGE):latest

# we can't use rootless podman here b/c we can't mount ~/.ssh inside (0400)
run: recipe.yaml
	docker run -it --rm --net=host \
		-u 1000 \
		-e FLASK_ENV=development \
		-e PAGURE_USER_TOKEN \
		-e PAGURE_FORK_TOKEN \
		-e GITHUB_TOKEN \
		-w /src \
		-v ~/.ssh/:/home/packit/.ssh/:Z \
		-v $(CURDIR):/src:Z \
		$(PACKIT_IMAGE) bash

prepare-check:
	ansible-playbook -b -K -i inventory-local -c local ./recipe-tests.yaml

check:
	tox

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

# build-tests: recipe-tests.yaml
# 	ansible-bender build -- ./recipe-tests.yaml $(SOURCE_GIT_IMAGE) $(PACKIT_TESTS_IMAGE)

# shell:
# 	podman run --rm -ti -v $(CURDIR):/src:Z -w /src $(PACKIT_TESTS_IMAGE) bash

# we should probably run tests in a root container (sudo podman)
# getting these type of errors with rootless:
#   error: [Errno 13] Permission denied: '/src/.tox/py36/lib/python3.6/site-packages/rpm-4.14.2.1-py3.6-linux-x86_64.egg'
# even though it doesn't make any sense: after tox fails, I can access the file
# just fine: a bug in fuse-overlayfs?
# test-in-container:
# 	podman run --rm -ti -v $(CURDIR):/src:Z -w /src $(PACKIT_TESTS_IMAGE) make check
