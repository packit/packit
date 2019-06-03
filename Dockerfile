FROM fedora:30

RUN dnf -y install ansible

COPY files/install-requirements.yaml .
COPY packit.spec .
RUN ansible-playbook -c local -i localhost, ./install-requirements.yaml

WORKDIR /src
