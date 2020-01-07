
TMP = $(CURDIR)/tmp
VERSION = $(shell grep ^Version edd.spec | sed 's/.* //')

# Push files to the production web only when in the master branch
ifeq "$(shell git rev-parse --abbrev-ref HEAD)" "master"
PUSH_URL = fedorapeople.org:public_html/edd
else
PUSH_URL = fedorapeople.org:public_html/edd/testing
endif

PACKAGE = edd-$(VERSION)
DOCS = $(TMP)/$(PACKAGE)/docs
CSS = --stylesheet=style.css --link-stylesheet
FILES = LICENSE README.rst \
		Makefile edd.spec \
		edd docs

all: push clean

build:
	mkdir -p $(TMP)/{SOURCES,$(PACKAGE)}
	cp -a $(FILES) $(TMP)/$(PACKAGE)
	cp docs/man.rst $(TMP)
	tail -n+16 README.rst >> $(TMP)/man.rst
	echo "man rst" | gzip > $(DOCS)/edd.1.gz
	echo "man html" > $(DOCS)/index.html

tarball: build
	cd $(TMP) && tar cfj SOURCES/$(PACKAGE).tar.bz2 $(PACKAGE)

rpm: tarball
	rpmbuild --define '_topdir $(TMP)' -bb edd.spec

srpm: tarball
	rpmbuild --define '_topdir $(TMP)' -bs edd.spec

packages: rpm srpm

push: packages
	# Documentation & examples
	scp $(DOCS)/*.{css,html} $(PUSH_URL)
	# Archives & rpms
	scp edd.spec \
		$(TMP)/SRPMS/$(PACKAGE)* \
		$(TMP)/RPMS/noarch/$(PACKAGE)* \
		$(TMP)/SOURCES/$(PACKAGE).tar.bz2 \
		$(PUSH_URL)/download

# Packit stuff
packit-tarball: tarball
	@printf "$(shell realpath $(TMP)/SOURCES/$(PACKAGE).tar.bz2)\n"
packit-version:
	@printf "$(VERSION)"

clean:
	rm -rf $(TMP)
