# pip3 install packit from this repo.

FROM quay.io/packit/base:fedora

WORKDIR /src

COPY files/tasks/*.yaml files/tasks/
COPY files/install-requirements-rpms.yaml files/
COPY *.spec ./
RUN ansible-playbook -v -c local -i localhost, files/install-requirements-rpms.yaml \
    && dnf clean all

COPY ./ ./
RUN pip3 install ./ \
    && git rev-parse HEAD >/.packit.git.commit.hash \
    && git show --quiet --format=%B HEAD >/.packit.git.commit.message \
    && rm -rf ~/.cache/*

ENV KRB5CCNAME=/tmp/ccache
