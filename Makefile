IMAGE=docker.io/usercont/packit
TESTS_IMAGE=packit-tests

CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)
TESTS_RECORDING_PATH=tests_recording
TESTS_TARGET ?= ./tests/unit ./tests/integration ./tests/functional


# To build base image for packit-worker
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

# example: TESTS_TARGET=tests/unit/test_api.py make check_in_container
check_in_container: tests_image
	$(CONTAINER_ENGINE) run --rm -ti \
		--env TESTS_TARGET \
		-v $(CURDIR):/src \
		--security-opt label=disable \
		$(TESTS_IMAGE) \
		bash -c "pip3 install .; make check"

# Mounts your ~/.config/ where .packit.yaml with your github/gitlab tokens is expected
check_in_container_regenerate_data: tests_image
	$(CONTAINER_ENGINE) run --rm -ti \
		--env TESTS_TARGET=$(TESTS_RECORDING_PATH) \
		-v $(CURDIR):/src \
		-v $(HOME)/.config:/root/.config \
		--security-opt label=disable \
		$(TESTS_IMAGE) \
		bash -c "pip3 install .; make check"
