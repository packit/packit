PACKAGE_NAME := cockpit-ostree
VERSION := $(shell T=$$(git describe 2>/dev/null) || T=1; echo $$T | tr '-' '.')

#
# Build/Install/dist
#

%.spec: %.spec.in
	sed -e 's/@VERSION@/$(VERSION)/g' $< > $@

dist-gzip: $(PACKAGE_NAME).spec
	tar czf $(PACKAGE_NAME)-$(VERSION).tar.gz --transform 's,^,$(PACKAGE_NAME)/,' \
		--exclude $(PACKAGE_NAME).spec.in \
		$$(git ls-files) $(PACKAGE_NAME).spec dist/ node_modules
