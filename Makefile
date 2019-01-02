BASE_IMAGE := registry.fedoraproject.org/fedora:29
TEST_TARGET := ./tests/
PY_PACKAGE := sourcegit
SOURCE_GIT_IMAGE := sourcegit

build: recipe.yaml
	sudo ansible-bender build --build-volumes $(CURDIR):/src:Z -- ./recipe.yaml $(BASE_IMAGE) $(SOURCE_GIT_IMAGE)

check:
	PYTHONPATH=$(CURDIR) pytest-3 -v $(TEST_TARGET)

shell:
	sudo podman run --rm -ti -v $(CURDIR):/src:Z -w /src $(SOURCE_GIT_IMAGE) bash

check-pypi-packaging:
	sudo podman run --rm -ti -v $(CURDIR):/src:Z -w /src $(SOURCE_GIT_IMAGE) bash -c '\
		set -x \
		&& rm -f dist/* \
		&& python3 ./setup.py sdist bdist_wheel \
		&& pip3 install dist/*.tar.gz \
		&& sourcegit --help \
		&& pip3 show $(PY_PACKAGE) \
		&& twine check ./dist/* \
		&& python3 -c "import sourcegit; assert sourcegit.__version__" \
		&& python3 -c "import onegittorulethemall" \
		&& pip3 show -f $(PY_PACKAGE) | ( grep test && exit 1 || :) \
		'

secrets.yaml:
	stat secrets.yaml || echo "Please create a file secrets.yaml and add two keys there: github_token and pagure_token"

run-local: secrets.yaml
	ansible-playbook -e source_git_image=$(SOURCE_GIT_IMAGE) -e @secrets.yaml -i inventory-local -c local ./deploy.yaml
	podman logs -f watcher & podman logs -f syncer & sleep 999999
