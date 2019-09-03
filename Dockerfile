# pip3 install packit from this repo.
# To build packit image on docker hub.

FROM fedora:30

ENV ANSIBLE_STDOUT_CALLBACK=debug \
    WORKDIR=/src

WORKDIR ${WORKDIR}

RUN dnf -y install ansible

COPY files/tasks/*.yaml ${WORKDIR}/files/tasks/
COPY files/install-requirements.yaml ${WORKDIR}/files/
COPY *.spec ${WORKDIR}/
RUN ansible-playbook -v -c local -i localhost, ${WORKDIR}/files/install-requirements.yaml \
    && dnf clean all

COPY ./ ${WORKDIR}/
RUN pip3 install ${WORKDIR}/ \
    && rm -rf ~/.cache/*

RUN cd / && rm -rf ${WORKDIR}/ && mkdir ${WORKDIR}/
