FROM fedora:30

RUN dnf -y install ansible

ENV ANSIBLE_STDOUT_CALLBACK=debug

COPY files/install-requirements.yaml packit.spec ./
RUN ansible-playbook -v -c local -i localhost, ./install-requirements.yaml

WORKDIR /src
