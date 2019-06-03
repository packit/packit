CONTAINER_NAME=packit
CONTAINER_EXEC=podman exec $(CONTAINER_NAME)

test_container: test_container_remove
	rsync -a $(CURDIR)/ /tmp/packit
	podman build --tag $(CONTAINER_NAME) .
	podman run --name $(CONTAINER_NAME) -ti -d -v /tmp/packit:/src:Z $(CONTAINER_NAME)
	sleep 2

test_container_remove:
	podman stop $(CONTAINER_NAME) || true
	podman rm -f $(CONTAINER_NAME) || true
	podman image rm $(CONTAINER_NAME) || true

install:
	pip3 install .

check: install
	PYTHONDONTWRITEBYTECODE=1 python3 -m pytest --color=yes --verbose --showlocals --cov=packit --cov-report=term-missing tests

check_in_container: test_container
	$(CONTAINER_EXEC) make check
