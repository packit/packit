FROM registry.fedoraproject.org/f29/httpd:2.4

ENV LANG=en_US.UTF-8
# nicer output from the playbook run
ENV ANSIBLE_STDOUT_CALLBACK=debug
# Ansible doesn't like /tmp
COPY files/ /src/files/
# We need to install packages. In httpd:2.4 container is user set to 1001
USER 0

# Commented. In httpd:2.4 image /usr/bin/python already exists
#RUN ln -s /usr/bin/python3 /usr/bin/python && \
RUN dnf install -y ansible

# Install packages first and reuse the cache as much as possible
RUN cd /src/ \
    && ansible-playbook -vv -c local -i localhost, files/install-rpm-packages.yaml

COPY setup.py setup.cfg recipe.yaml .git_archival.txt .gitattributes /src/
# setuptools-scm
COPY .git /src/.git
COPY packit/ /src/packit/

RUN cd /src/ \
    && ansible-playbook -vv -c local -i localhost, recipe.yaml

# TODO: add this logic to recipe.yaml
RUN /usr/libexec/httpd-prepare && rpm-file-permissions \
    && chmod -R a+rwx /var/lib/httpd \
    && chmod -R a+rwx /var/log/httpd

USER 1001

CMD ["/usr/bin/run-httpd"]
