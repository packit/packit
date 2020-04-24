# pip3 install packit from this repo.
# Base image for packit-service-worker

FROM fedora:31

ENV ANSIBLE_PYTHON_INTERPRETER=/usr/bin/python3 \
    ANSIBLE_STDOUT_CALLBACK=debug \
    WORKDIR=/src

WORKDIR ${WORKDIR}

RUN dnf -y install ansible

COPY files/tasks/*.yaml ${WORKDIR}/files/tasks/
COPY files/install-build-deps.yaml ${WORKDIR}/files/
COPY *.spec ${WORKDIR}/
RUN ansible-playbook -v -c local -i localhost, ${WORKDIR}/files/install-build-deps.yaml \
    && dnf clean all

COPY ./ ${WORKDIR}/
RUN pip3 install ${WORKDIR}/ \
    && cd ${WORKDIR} && git rev-parse HEAD >/.packit.git.commit.hash \
    && git show --quiet --format=%B HEAD >/.packit.git.commit.message \
    && rm -rf ~/.cache/*

RUN cd / && rm -rf ${WORKDIR}/ && mkdir ${WORKDIR}/
