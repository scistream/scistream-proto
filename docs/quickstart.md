# 3. Getting Started with Scistream

This page is aimed at users who are new to Scistream and want to quickly set up and run their first data streaming workflow. We will cover the installation process, dependencies, and a simple example to help you get started.

## 3.1 Prerequisites

Before you begin, make sure you have the following dependencies installed:

- Docker: Scistream relies on Docker to spin up Scistream Data Server (S2DS) instances. Please ensure that you have Docker installed and running on your system.
- Python: Scistream has been tested and developed using Python 3.9.2. While it may work with other versions, we recommend using Python 3.9.2 to avoid any compatibility issues.

Note: If you encounter any issues during the installation or setup process, we recommend using our reference Vagrant environment, which provides a pre-configured Ubuntu-based development environment.

## 3.2 Installation

1. Download the Scistream package by clicking [here](dist/scistream_proto-1.0.0-py3-none-any.whl).

2. Install the downloaded package using pip:

```bash
pip install scistream_proto-1.0.0-py3-none-any.whl
```

## 3.3 Starting the Scistream Control Server

To start the Scistream Control Server (S2CS), run the following command in a new terminal:


```bash
s2cs -t Haproxy --verbose
```

You should see the following output, indicating that the server has started successfully:

```text
Server started on 0.0.0.0:5000
```

## 3.4 Sending a Request using Scistream User Client

Once the control server is running, you can send a request using the Scistream User Client (S2UC). Run the following command in a separate terminal:

```bash
s2uc prod-req --mock True
```

The output will look similar to this:

```text
uid; s2cs; access_token; role
4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 localhost:5000 INVALID_TOKEN PROD
waiting for hello message
started client request
```

## 3.5 Running the Application Controller Mock

To simulate a producer or consumer application, you can run the application controller mock using the following command in a different terminal:

```bash
appctrl mock 4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 localhost:5000 INVALID_TOKEN PROD 10.0.0.1
```

## 3.6 Releasing the Request

To release the request and clean up the resources, use the following command in the terminal where you ran the S2UC command:

```bash
s2uc release 4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3
```

Congratulations! You have now successfully installed Scistream, started the control server, sent a request using the user client, and run a mock application controller.

For more detailed information and advanced usage, please refer to the complete [User Guide](guides/user.md).

## Troubleshooting

- If you encounter permission issues related to Docker, consider adding your user to the Docker group by following the instructions in this tutorial: [Manage Docker as a non-root user.](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)
