Vagrant.configure("2") do |config|
    if Vagrant.has_plugin?("vagrant-vbguest")
        config.vbguest.auto_update = false
    end

    config.vm.box = "fedora/29-cloud-base"
    config.vm.box_version = "29.20181024.1"
    config.vm.synced_folder ".", "/vagrant"

    config.vm.provider "virtualbox" do |virtualbox|
        virtualbox.memory = 1024
    end

    config.vm.provision "shell", inline: <<-SHELL
        set -x
        dnf install -y ansible
    SHELL

    config.vm.provision :ansible_local do |ansible|
	    ansible.verbose = "v"
	    ansible.playbook = "files/install-rpm-packages.yaml"
	    ansible.extra_vars = { ansible_python_interpreter: "/usr/bin/python3" }
	    ansible.become = true
    end
    config.vm.provision "shell", inline: <<-SHELL
        pip3 install ogr
        cd /vagrant
        pip3 install .
    SHELL
end
