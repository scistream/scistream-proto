# Advanced Guide

This tutorial is intended for software engineers, system administrators, and users who wish to deeply understand the inner workings of SciStream, customize its functionality, or extend its capabilities. The tutorial assumes you've completed the other tutorials, have familiarity with the basic usage of SciStream and aims to provide a comprehensive guide for developers looking to contribute to the project or integrate with the SciStream framework.

### Prerequisites and required knowledge

To fully benefit from this tutorial, you should have the following prerequisites and knowledge:

Some proficiency in python.
Familiarity with network protocols (TCP/IP, UDP) and concepts (routing, NAT, firewalls), docker

## Setting Up the Development Environment

We use [poetry](https://python-poetry.org/docs/) to manage our python environments. Please ensure you have Python 3.9+ and poetry installed in your environment. We require docker for using the Haproxy and NGINX S2DS implementation. We provide a setup scrit that was used to install these dependencies on the Fabric platform. This installation script was tested on ubuntu 20.04 version.

Before building SciStream from source, install the necessary dependencies:

- Python 3.9+
- Docker Engine
- Poetry

Once you have the dependencies the following commands download and installs all the necessary python dependencies. It also activates the virtual environment.

~~~
poetry install
poetry shell
~~~

# Software components

## S2DS and ProxyContainer Documentation

The code consists of the `S2DS` python class and `ProxyContainer` subclasses, including `Haproxy`, `Nginx`, `Janus`, and `DockerSock`, which serve to establish and manage the data streaming pipelines. It uses docker to bring up a Haproxy container, its configuration is built by S2DS using the information provided by S2CS.

If S2CS is unavailable, S2DS continues to work as before. Modifications to S2DS are performed by S2CS.

### S2DS Class

The `S2DS` class is responsible for managing the lifecycle of S2DS subprocesses. It includes methods for starting subprocesses, managing listener ports, and releasing resources. The `start` method initiates a specified number of subprocesses, dynamically allocating ports and creating listener addresses. It also handles error conditions gracefully, raising a custom `S2DSException` when encountering issues. The `release` and `update_listeners` methods provide mechanisms for terminating subprocesses and updating connection information, respectively.

### ProxyContainer and Subclasses

The `ProxyContainer` class and its subclasses (`Haproxy`, `Nginx`, `Janus`, `DockerSock`) are a specific implementation of S2DS and they abstract the complexities of deploying proxy containers to facilitate. These classes are designed to work with different Docker plugins and configurations, allowing for flexible deployment scenarios. Each subclass specifies its own container configuration, including the image name, container name, and configuration file locations. The `start` method in each class leverages Docker APIs to deploy and manage containers based on the provided configuration. Additionally, the `update_listeners` method in `ProxyContainer` demonstrates how to dynamically update listener configurations using Jinja2 templates.

#
