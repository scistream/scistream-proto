Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-22.04"

  # Ansible provisioner
  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "deploy/playbook.yml"
  end

  config.vm.define "producer" do |producer|
    producer.vm.hostname = "producer"
    producer.vm.network "private_network", ip: "192.168.10.10"
  end

  config.vm.define "producers2" do |producers2|
    producers2.vm.hostname = "producers2"
    producers2.vm.network "private_network", ip: "192.168.10.11"
    producers2.vm.network "private_network", ip: "192.168.20.10"
  end

  config.vm.define "consumers2" do |consumers2|
    consumers2.vm.hostname = "consumers2"
    consumers2.vm.network "private_network", ip: "192.168.20.11"
    consumers2.vm.network "private_network", ip: "192.168.30.10"
  end

  config.vm.define "consumer" do |consumer|
    consumer.vm.hostname = "consumer"
    consumer.vm.network "private_network", ip: "192.168.30.11"
  end
end
