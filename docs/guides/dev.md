# 6 Advanced SciStream Tutorial for Developers

## 6.1 Introduction

SciStream is a framework designed to enable high-speed, memory-to-memory data streaming between scientific instruments and remote computing facilities. This tutorial aims to provide developers with an in-depth understanding of SciStream's architecture and guide them through the process of setting up a SciStream environment using virtual machines (VMs) and running SciStream from the source code. By the end of this tutorial, developers will be equipped with the knowledge and skills necessary to modify, extend, and deploy SciStream based on their specific requirements.

### 6.1.1 Prerequisites

- Familiarity with Python programming
- Basic understanding of virtualization and VM management
- Vagrant installed
- Knowledge of networking concepts and docker
- Experience with command-line interfaces

### 6.1.2 Setting up a SciStream Environment with VMs

In this part of the tutorial, we will walk through the steps to set up a SciStream environment using vagrant. This approach allows developers to create isolated and reproducible environments for development and testing purposes.

### 6.1.3 Preparing the Development Environment

**System Requirements:**

- A host machine with sufficient resources to run multiple VMs
- Virtualization software (e.g., VirtualBox recommended )
- Operating system: MacOs or Linux (recommended)

**Setting up Virtual Machines (VMs):**

We have a reference vagrant file in the root folder.

```
vagrant up
```

## Generate Digital Certificates

```
vagrant ssh producers2
openssl genrsa -out server.key 2048
```
Create a file named server.conf with the following content:
```
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = 192.168.10.11

[v3_req]
subjectAltName = IP:192.168.10.11
```
Then let's create the certificates
```
openssl req -new -key server.key -out server.csr -config server.conf
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt -extfile server.conf -extensions v3_req
```

## 6.2 Start Scistream components

- On the producer S2CS machine, start the SciStream Control Server with the appropriate configuration:

```
vagrant ssh producers2
s2cs --verbose --port=5007 --listener-ip=192.168.10.11 --type=Haproxy
```

- On the producer machine, initiate a producer request to specify the stream endpoint details. Notice that the --mock flag hardcodes the uid of the request for reproducibility purposes:

```
vagrant ssh producer
cp ./vagrant/server.crt ./server.crt
s2uc prod-req --s2cs 192.168.10.11:5007 --mock True
```

Note down the unique ID (uid) generated for the producer request.

The control server will be waiting for the hello message.

- On a second terminal of the producer machine. Run the application controller mock using the following command:

```
vagrant ssh producer
cp ./vagrant/server.crt ./server.crt
appctrl mock 4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 192.168.10.11:5007 INVALID_TOKEN PROD 192.168.10.10
```

Notice the hello message informs s2cs the forwarding address and port to which the scistream will forward the traffic. In this example, the appctrl script hardcodes the ports, the application address is the last parameter. The appctrl in this case is a thin client and can be thought of as a reference implementation.

- On the consumer S2CS machine, start the SciStream Control Server with the appropriate configuration. Note that client_id and client_secret need to be generated accordingly as described in the authorization tutorial.

```
vagrant ssh consumers2
s2cs --verbose --port=5007 --listener-ip=192.168.30.10 --type=Haproxy --client-id "abc" --client-secret
```

- Now, on the consumer machine, login and initiate a consumer request to specify the stream endpoint details. Replace `<uid>` with the unique ID obtained from the producer request.

```
vagrant ssh consumer
cp ./vagrant/server.crt ./server.crt
s2uc login --scope "abc"
s2uc cons-req --s2cs 192.168.30.10:5007 4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 192.168.20.10:5074
```
The control server will be waiting for the hello message to complete the resource reservation.

- On a second terminal of consumer machine. Run the application controller mock using the following command:

```
cp ./vagrant/server.crt ./server.crt
appctrl mock 4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 192.168.30.10:5007 INVALID_TOKEN PROD 192.168.20.10
```

The hello message informs s2cs the forwarding address and port to which the scistream will forward the traffic. In this example, the appctrl script hardcodes the ports, the application address is the last parameter. The appctrl in this case is a thin client and can be thought of as a reference implementation.

## 6.3 Start producer and consumer application

- On the producer machine, start iPerf in server mode:

```
vagrant ssh producer
iperf -s -p 5001
```

- On the consumer machine, start iPerf in client mode:

```
iperf -c 10.16.42.12 -p 5001 -t 60
```

  This command will initiate a 60-second data stream from the producer to the consumer.

- On the S2UC machine, monitor the status of the stream flow:

```
python src/s2uc.py check-status <uid>
```

  Replace `<uid>` with the unique ID of the stream flow.

- Verify that data is being transferred successfully from the producer to the consumer by checking the iPerf output on both machines.
- Check for any errors or performance bottlenecks in the SciStream logs on the S2CS and S2
