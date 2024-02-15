# Developer Guide

## Software components
* **SciStream Data Server (S2DS):** software that runs on gateway nodes. It acts as a buffer-and-forward agent.
* **SciStream User Client (S2UC):** software that the end user and/or workflow engines/tools acting on behalf of the user interact with and provide relevant information (e.g., ID of a HPC job, ID of an experiment or data acquisition job on a scientific instrument, shared secret for secure communication with the user job (application) at the producer and consumer) to orchestrate end-to-end data streaming.
* **SciStream Control Server (S2CS):** a software running on one of the gateway nodes. It interacts with S2UC, data producer/consumer and S2DS.

## S2DS and ProxyContainer Documentation

The code consists mainly of the `S2DS` class and `ProxyContainer` subclasses, including `Haproxy`, `Nginx`, `Janus`, and `DockerSock`, which serve to establish and manage the data streaming pipelines using various networking and container technologies.

### S2DS Class

The `S2DS` class is responsible for managing the lifecycle of S2DS subprocesses, which are the forwarding element of the data streaming . It includes methods for starting subprocesses, managing listener ports, and releasing resources. The `start` method initiates a specified number of subprocesses, dynamically allocating ports and creating listener addresses. It also handles error conditions gracefully, raising a custom `S2DSException` when encountering issues. The `release` and `update_listeners` methods provide mechanisms for terminating subprocesses and updating connection information, respectively.

### ProxyContainer and Subclasses

The `ProxyContainer` class and its subclasses (`Haproxy`, `Nginx`, `Janus`, `DockerSock`) are a specific implementation of S2DS and they abstract the complexities of deploying proxy containers to facilitate. These classes are designed to work with different Docker plugins and configurations, allowing for flexible deployment scenarios. Each subclass specifies its own container configuration, including the image name, container name, and configuration file locations. The `start` method in each class leverages Docker APIs to deploy and manage containers based on the provided configuration. Additionally, the `update_listeners` method in `ProxyContainer` demonstrates how to dynamically update listener configurations using Jinja2 templates.

## Developer environment Tutorial

## Pre-requisites
We use [poetry](https://python-poetry.org/docs/) to manage our python environments. Please ensure you have Python 3.9+ and poetry installed in your environment. We require docker for using the Haproxy and NGINX S2DS implementation. We provide a setup scrit that was used to install these dependencies on the Fabric platform. This installation script was tested on ubuntu 20.04 version.

We also use a Git submodules to manage dependencies, such as the original S2DS implementation project. To set up the SciStream Data Server (S2DS) submodule, run the following commands:

~~~
git submodule init
git submodule update
cd scistream/S2DS
make
cd ../../
~~~

This process initializes, updates, and compiles the submodule, streamlining your project setup and ensuring compatibility with the latest version of the parent project.


## Quick Start

Once you have the dependencies the following commands download and installs all the necessary python dependencies. It also activates the virtual environment.

~~~
poetry install
poetry shell
~~~~

The easiest way to verify if the code works is to run pytest:

~~~
poetry run pytest
~~~

The output of the test should look like this:

~~~
========================================== test session starts ==========================================
platform linux -- Python 3.9.16, pytest-7.2.2, pluggy-1.0.0
rootdir: /home/fcastro/dev/scistream-proto
plugins: timeout-2.1.0
collected 6 items                                                                                       

tests/test_s2cs.py .x....                                                                         [100%]

===================================== 5 passed, 1 xfailed in 5.81s ======================================
~~~

Once this runs all the
## Tutorial

### Authentication

We integrated with globus platform for the purpose of authentication.

If your token expired you might want to start by logging out.
~~~
$ python src/s2uc.py logout
~~~

After that let's log in:

~~~
$ python src/s2uc.py login
~~~

You will see a URL. You need to open the url provided in a web browser, log in with the proper credentials, then copy and paste the authorization code into the cli prompt.

~~~
(scistream-proto-py3.9) bash-3.2$ python src/s2uc.py login
Please authenticate with Globus here:
```------------------------------------
https://auth.globus.org/v2/oauth2/authorize?client_id=4787c84e-9c55-a11c&redirect_uri=https%3A%2F%2Fauth.globus.org=login
------------------------------------```

Enter the resulting Authorization Code here:
~~~

After logging in you can move to the next tutorial step.

### Running scistream

To understand the behavior of the code let's simulate the environment by opening 3 terminals, 1 for the s2cs Producer, 1 for s2cs Consumer, and one for the client terminal.

To run this you will need to open multiple terminals:

~~~
python src/s2cs.py --port=5000 --listener-ip=10.133.137.2 --verbose --type=Haproxy
python src/s2uc.py prod-req --s2cs 10.133.137.2:5000

python src/appcontroller.py create-appctrl cac92bb0-7345-11ee-9876-bff742c41932 10.130.134.2:5000 AgpQoBo1VvvYkz8yYxyQgkgrW7nobYmG6dno8q8rgKG9MMYDM2IvCjgEezy8mqJpqvMl44GDq5GKayTyvkXn4fdmoB2 PROD 10.133.139.2

python src/s2uc.py cons-req --s2cs 10.130.134.2:5000 cac92bb0-7345-11ee-9876-bff742c41932 10.133.137.2:5001

python src/appcontroller.py create-appctrl cac92bb0-7345-11ee-9876-bff742c41932 10.130.134.2:5000 AgpQoBo1VvvYkz8yYxyQgkgrW7nobYmG6dno8q8rgKG9MMYDM2IvCjgEezy8mqJpqvMl44GDq5GKayTyvkXn4fdmoB2 CONS 10.130.133.2
~~~

Several things will happen in the background to learn more please review the code. The output of the client should look like this:

~~~
listeners: "0.0.0.0:43579"
listeners: "0.0.0.0:34375"
listeners: "0.0.0.0:34343"
listeners: "0.0.0.0:38223"
listeners: "0.0.0.0:34865"
prod_listeners: "127.0.0.1:7000"
prod_listeners: "127.0.0.1:17000"
prod_listeners: "127.0.0.1:27000"
prod_listeners: "127.0.0.1:37000"
prod_listeners: "127.0.0.1:47000"

Sending updated connection map information...
82f0e9b8-eb7d-11ed-be3c-f303ca66dd31
~~~
In this case 82f0e9b8-eb7d-11ed-be3c-f303ca66dd31 is the uid, let's use that to send a release:
~~~
$ python src/s2uc.py release 82f0e9b8-eb7d-11ed-be3c-f303ca66dd31
Release completed
~~~
