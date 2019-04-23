FROM registry.fedoraproject.org/fedora:29

ENV LANG=en_US.UTF-8
# nicer output from the playbook run
ENV ANSIBLE_STDOUT_CALLBACK=debug

RUN ln -s /usr/bin/python3 /usr/bin/python && \
    dnf install -y ansible

COPY . /src/

RUN cd /src/ \
    && ansible-playbook -vv -c local -i localhost, recipe.yaml \
    && dnf remove -y ansible \
    && dnf clean all

ENV USER=packit \
    HOME=/home/packit/ \
    NSS_WRAPPER_PASSWD=/home/packit/passwd \
    NSS_WRAPPER_GROUP=/etc/group \
    LD_PRELOAD=libnss_wrapper.so \
    FLASK_APP=packit.service.web_hook

CMD ["flask-3", "run", "-h", "0.0.0.0"]
