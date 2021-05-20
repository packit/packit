IMAGE=quay.io/packit/packit
TESTS_IMAGE=packit-tests

CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)
TESTS_RECORDING_PATH=tests_recording
TESTS_TARGET ?= ./tests/unit ./tests/integration ./tests/functional
CONTAINER_RUN_WITH_OPTS=$(CONTAINER_ENGINE) run --rm -ti -v $(CURDIR):/src --security-opt label=disable
CONTAINER_TEST_COMMAND=bash -c "pip3 install .; make check"

# In case you don't want to use pre-built image
image:
	$(CONTAINER_ENGINE) build --rm --tag $(IMAGE) .

tests_image:
	$(CONTAINER_ENGINE) build --rm --tag $(TESTS_IMAGE) -f Dockerfile.tests .
	sleep 2

tests_image_remove:
	$(CONTAINER_ENGINE) rmi $(TESTS_IMAGE)

install:
	pip3 install --user .

check:
	find . -name "*.pyc" -exec rm {} \;
	PYTHONPATH=$(CURDIR) PYTHONDONTWRITEBYTECODE=1 python3 -m pytest --verbose --showlocals $(TESTS_TARGET)

requre_data_cleanup:
	requre-patch purge --replaces "copr.v3.helpers:login:str:somelogin" --replaces "copr.v3.helpers:token:str:sometoken" $(TESTS_RECORDING_PATH)/test_data/*/*yaml
	requre-patch create-symlinks $(CURDIR)/$(TESTS_RECORDING_PATH)/test_data/

# example: TESTS_TARGET=tests/unit/test_api.py make check_in_container
check_in_container: tests_image
	$(CONTAINER_RUN_WITH_OPTS) --env TESTS_TARGET $(TESTS_IMAGE) $(CONTAINER_TEST_COMMAND)

# Mounts your ~/.config/ where .packit.yaml with your github/gitlab tokens is expected
# Mounts ssh connfig dir, to have ssh keys for fedpkg cloning
# create random tmpdir and mount into /tmp to avoid issues with creating temporary dirs via python
check_in_container_regenerate_data: tests_image
	$(eval RANDOM_TMP_DIR = $(shell mktemp -d))
	$(CONTAINER_RUN_WITH_OPTS) --env TESTS_TARGET="$(TESTS_RECORDING_PATH)" -v $(RANDOM_TMP_DIR):/tmp -v $(HOME)/.ssh:/root/.ssh -v $(HOME)/.config:/root/.config $(TESTS_IMAGE) $(CONTAINER_TEST_COMMAND)
	rm -fr $(RANDOM_TMP_DIR)
