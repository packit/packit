Vagrant.configure("2") do |config|
    if Vagrant.has_plugin?("vagrant-vbguest")
        config.vbguest.auto_update = false
    end

    config.vm.box = "fedora/30-cloud-base"
    config.vm.synced_folder ".", "/vagrant"

    config.vm.provider "virtualbox" do |virtualbox|
        virtualbox.memory = 1024
    end

    config.vm.provision "shell", inline: <<-SHELL
        dnf -y install ansible || true
    SHELL

    config.vm.provision :ansible_local do |ansible|
	    ansible.verbose = "v"
	    ansible.playbook = "files/install-build-deps.yaml"
	    ansible.become = true
    end

    config.vm.provision "shell", inline: <<-SHELL
        cd /vagrant
        pip3 install .
    SHELL
end
