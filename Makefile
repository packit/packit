CONTAINER_NAME=packit
TESTS_INTEGRATION_PATH=tests/integration
TEST_DATA_PATH=$(TESTS_INTEGRATION_PATH)/test_data
CONTAINER_RUN=podman run --rm -ti -v $(CURDIR):/src:Z $(CONTAINER_NAME)
TEST_TARGET := ./tests

test_container:
	podman build --tag $(CONTAINER_NAME) .
	sleep 2

test_container_remove:
	podman image rm $(CONTAINER_NAME)

install:
	pip3 install --user .

check:
	find . -name "*.pyc" -exec rm {} \;
	PYTHONPATH=$(CURDIR) PYTHONDONTWRITEBYTECODE=1 python3 -m pytest --verbose --showlocals --cov=packit --cov-report=term-missing $(TEST_TARGET)

check_in_container: test_container
	$(CONTAINER_RUN) bash -c "pip3 install .; make check TEST_TARGET=$(TEST_TARGET)"


check_in_container_regenerate_data: test_container
	$(CONTAINER_RUN) bash -c "pip3 install .;make check TEST_TARGET=$(TESTS_INTEGRATION_PATH) GITHUB_TOKEN=${GITHUB_TOKEN} PAGURE_TOKEN=${PAGURE_TOKEN}"
