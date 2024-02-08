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
