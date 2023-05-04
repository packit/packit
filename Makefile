IMAGE=quay.io/packit/packit
TEST_IMAGE=packit-tests

CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)
COLOR ?= yes
TEST_RECORDING_PATH=tests_recording
TEST_TARGET ?= ./tests/unit ./tests/integration ./tests/functional
TEST_TIMEOUT ?= 120
COV_REPORT ?= --cov=packit --cov-report=term-missing
CONTAINER_RUN_WITH_OPTS=$(CONTAINER_ENGINE) run --rm -ti -v $(CURDIR):/src --security-opt label=disable
CONTAINER_TEST_COMMAND=bash -c "pip3 install .; make check"

# In case you don't want to use pre-built image
image:
	$(CONTAINER_ENGINE) build --rm --tag $(IMAGE) -f Containerfile .

build-test-image:
	$(CONTAINER_ENGINE) build --rm --tag $(TEST_IMAGE) -f Containerfile.tests .

remove-test-image:
	$(CONTAINER_ENGINE) rmi $(TEST_IMAGE)

install:
	pip3 install --user .

check:
	find . -name "*.pyc" -exec rm {} \;
	PYTHONPATH=$(CURDIR) PYTHONDONTWRITEBYTECODE=1 python3 -m pytest --color=$(COLOR) --verbose --showlocals --timeout=$(TEST_TIMEOUT) $(COV_REPORT) $(TEST_TARGET)

requre-data-cleanup:
	requre-patch purge --replaces ":set-cookie:str:a 'b';" --replaces "copr.v3.helpers:login:str:somelogin" --replaces "copr.v3.helpers:token:str:sometoken" $(TEST_RECORDING_PATH)/test_data/*/*yaml
	requre-patch create-symlinks $(CURDIR)/$(TEST_RECORDING_PATH)/test_data/

# example: TEST_TARGET=tests/unit/test_api.py make check-in-container
check-in-container:
	$(CONTAINER_RUN_WITH_OPTS) \
		--env TEST_TARGET \
		--env COV_REPORT \
		--env COLOR \
		$(TEST_IMAGE) $(CONTAINER_TEST_COMMAND)

# Mounts your ~/.config/ where .packit.yaml with your github/gitlab tokens is expected
# Mounts ssh connfig dir, to have ssh keys for fedpkg cloning
# create random tmpdir and mount into /tmp to avoid issues with creating temporary dirs via python
# if you are getting 'root@pkgs.fedoraproject.org: Permission denied (publickey)', you should initiatie a kerberos ticket in the container:
#   export KRB5CCNAME=FILE:/tmp/k && kinit $USER@FEDORAPROJECT.ORG
check-in-container-regenerate-data:
	$(eval RANDOM_TMP_DIR = $(shell mktemp -d))
	$(CONTAINER_RUN_WITH_OPTS) --env TEST_TARGET="$(TEST_RECORDING_PATH)" -v $(RANDOM_TMP_DIR):/tmp -v $(HOME)/.ssh:/root/.ssh -v $(HOME)/.config:/root/.config $(TEST_IMAGE) $(CONTAINER_TEST_COMMAND)
	rm -fr $(RANDOM_TMP_DIR)
