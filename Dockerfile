FROM fedora:30

RUN dnf -y install ansible

ENV ANSIBLE_STDOUT_CALLBACK=debug

COPY files/*.yaml files/
COPY files/tasks/*.yaml files/tasks/
COPY *.spec .
RUN  ansible-playbook -v -c local -i localhost, files/install-requirements.yaml

WORKDIR /src
