CONTAINER_NAME=packit
CONTAINER_RUN=podman run --rm -ti -v /tmp/packit:/src:Z $(CONTAINER_NAME)
TEST_TARGET := ./tests/

test_container:
	podman build --tag $(CONTAINER_NAME) .
	sleep 2

test_container_remove:
	podman image rm $(CONTAINER_NAME)
install:
	pip3 install --user .

check:
	find . -name "*.pyc" -exec rm {} \;
	PYTHONPATH=$(CURDIR) PYTHONDONTWRITEBYTECODE=1 python3 -m pytest --color=yes --verbose --showlocals --cov=packit --cov-report=term-missing $(TEST_TARGET)

check_in_container: test_container
	rsync -a $(CURDIR)/ /tmp/packit
	$(CONTAINER_RUN) bash -c "pip3 install .; make check"
