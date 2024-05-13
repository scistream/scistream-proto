# Define the Vagrant configuration version
Vagrant.configure("2") do |config|
  # Define the base box (Ubuntu)
  config.vm.box = "bento/ubuntu-22.04"

  # Copy the wheel file to each VM
  config.vm.provision "file", source: "docs/dist/scistream_proto-0.2.1-py3-none-any.whl", 
destination: "scistream_proto-1.0.0-py3-none-any.whl"

  # Provisioning to install Docker and the Python package
  config.vm.provision "shell", inline: <<-SHELL
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    sudo apt-get update
    sudo apt-get install -y docker-ce
    sudo apt-get install -y iperf3
    sudo usermod -aG docker vagrant
    sudo apt-get install -y python3-pip
    pip3 install scistream_proto-0.2.2-py3-none-any.whl
  SHELL

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
