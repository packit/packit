TESTS_IMAGE=packit-tests
TESTS_RECORDING_PATH=tests_recording
TESTS_CONTAINER_RUN=podman run --rm -ti -v $(CURDIR):/src --security-opt label=disable $(TESTS_IMAGE)
TESTS_TARGET := ./tests/unit ./tests/integration ./tests/functional

tests_image:
	podman build --tag $(TESTS_IMAGE) -f Dockerfile.tests .
	sleep 2

tests_image_remove:
	podman rmi $(TESTS_IMAGE)

install:
	pip3 install --user .

check:
	find . -name "*.pyc" -exec rm {} \;
	PYTHONPATH=$(CURDIR) PYTHONDONTWRITEBYTECODE=1 python3 -m pytest --verbose --showlocals $(TESTS_TARGET)

check_in_container: tests_image
	$(TESTS_CONTAINER_RUN) bash -c "pip3 install .; make check"


check_in_container_regenerate_data: tests_image
	$(TESTS_CONTAINER_RUN) bash -c "pip3 install .;make check TESTS_TARGET=$(TESTS_RECORDING_PATH) GITHUB_TOKEN=${GITHUB_TOKEN} PAGURE_TOKEN=${PAGURE_TOKEN}"
