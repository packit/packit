IMAGE=docker.io/usercont/packit
TESTS_IMAGE=packit-tests

CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)
TESTS_CONTAINER_RUN=$(CONTAINER_ENGINE) run --rm -ti -v $(CURDIR):/src --env TESTS_TARGET --security-opt label=disable $(TESTS_IMAGE)
TESTS_RECORDING_PATH=tests_recording
TESTS_TARGET ?= ./tests/unit ./tests/integration ./tests/functional


# To build base image for packit-service-worker
image:
	$(CONTAINER_ENGINE) build --rm -t $(IMAGE) .

tests_image:
	$(CONTAINER_ENGINE) build --tag $(TESTS_IMAGE) -f Dockerfile.tests .
	sleep 2

tests_image_remove:
	$(CONTAINER_ENGINE) rmi $(TESTS_IMAGE)

install:
	pip3 install --user .

check:
	find . -name "*.pyc" -exec rm {} \;
	PYTHONPATH=$(CURDIR) PYTHONDONTWRITEBYTECODE=1 python3 -m pytest --verbose --showlocals $(TESTS_TARGET)

check_in_container: tests_image
	$(TESTS_CONTAINER_RUN) bash -c "pip3 install .; make check"


check_in_container_regenerate_data: tests_image
	$(TESTS_CONTAINER_RUN) bash -c "pip3 install .;make check TESTS_TARGET=$(TESTS_RECORDING_PATH) GITHUB_TOKEN=${GITHUB_TOKEN} PAGURE_TOKEN=${PAGURE_TOKEN}"
