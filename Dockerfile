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

COPY setup.py recipe.yaml /src/
# setuptools-scm
COPY .git /src/.git
COPY packit/ /src/packit/

RUN cd /src/ \
    && ansible-playbook -vv -c local -i localhost, recipe.yaml

#COPY ./files/httpd-packit.conf /etc/httpd/conf.d/httpd-packit.conf

RUN /usr/libexec/httpd-prepare && rpm-file-permissions \
    && chmod -R a+rwx /var/lib/httpd \
    && chmod -R a+rwx /var/log/httpd \
    && cp /src/files/httpd-copy.sh /usr/share/container-scripts/httpd/pre-init/50-httpd-copy.sh
#    && cp /src/files/acme-generate.sh /usr/share/container-scripts/httpd/pre-init/60-acme-generate.sh

USER 1001

CMD ["/usr/bin/run-httpd"]
