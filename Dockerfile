FROM registry.fedoraproject.org/fedora:29

ENV LANG=en_US.UTF-8
# nicer output from the playbook run
ENV ANSIBLE_STDOUT_CALLBACK=debug
RUN ln -s /usr/bin/python3 /usr/bin/python \
    && dnf install -y ansible

# Ansible doesn't like /tmp
COPY files/ /src/files/

# Install packages first and reuse the cache as much as possible
RUN cd /src/ \
    && ansible-playbook -vv -c local -i localhost, files/install-rpm-packages.yaml

COPY setup.py recipe.yaml /src/
# setuptools-scm
COPY .git /src/.git
COPY packit/ /src/packit/

RUN cd /src/ \
    && ansible-playbook -vv -c local -i localhost, recipe.yaml

ENV USER=packit \
    HOME=/home/packit/ \
    NSS_WRAPPER_PASSWD=/home/packit/passwd \
    NSS_WRAPPER_GROUP=/etc/group \
    LD_PRELOAD=libnss_wrapper.so \
    FLASK_APP=packit.service.web_hook

CMD ["flask-3", "run", "-h", "0.0.0.0"]
