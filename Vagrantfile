
Vagrant.configure("2") do |config|
    config.vm.box = "fedora/29-cloud-base"
    config.vm.box_version = "29.20181024.1"

    config.vm.provider "virtualbox" do |virtualbox|
        virtualbox.memory = 512
    end

    config.vm.provision "shell", inline: <<-SHELL
        set -x
        dnf install -y fedpkg git nss_wrapper python3-GitPython \
          python3-click python3-copr python3-devel python3-fedmsg \
          python3-flask python3-ipdb python3-jsonschema python3-libpagure \
          python3-mod_wsgi python3-munch python3-ogr python3-packaging \
          python3-pip python3-pygithub python3-pyyaml python3-requests \
          python3-rpm python3-setuptools python3-setuptools_scm python3-setuptools_scm_git_archive \
          python3-tabulate python3-wheel rebase-helper rpm-build krb5-workstation krb5-devel
        pip3 install ogr
        cd /vagrant
        pip3 install .
     SHELL
end
