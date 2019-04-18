FROM registry.fedoraproject.org/fedora:29

ENV LANG=en_US.UTF-8

RUN ln -s /usr/bin/python3 /usr/bin/python && \
    dnf install -y ansible

COPY recipe.yaml /tmp/
COPY files /tmp/files/
COPY . /src/

RUN cd /tmp/ && \
    ansible-playbook -vvv -c local -i localhost, recipe.yaml && \
    dnf remove -y ansible &&  dnf clean all

ENV USER=packit \
    HOME=/home/packit/ \
    NSS_WRAPPER_PASSWD=/home/packit/passwd \
    NSS_WRAPPER_GROUP=/etc/group \
    LD_PRELOAD=libnss_wrapper.so \
    FLASK_APP=packit.service.web_hook

CMD ["flask-3", "run", "-h", "0.0.0.0"]
