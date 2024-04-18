# 4. User Guide

## 4.1 Overview

SciStream is a framework and toolkit designed to enable high-speed, memory-to-memory data streaming between scientific instruments and remote computing facilities. It addresses the challenges of streaming data in scientific environments where data producers (e.g., scientific instruments) and consumers (e.g., analysis applications) are often located in different institutions with distinct security domains.

Key features of SciStream include:

- High-speed memory-to-memory data streaming (100Gbps+)
- Bridging of security domains between scientific instruments and remote computing facilities
- Integration with existing authentication and authorization systems (e.g., Globus Auth)
- Transparent and efficient connections between data producers and consumers
- Agnostic to data streaming libraries and applications

## 4.2 Prerequisites

Before using SciStream, ensure that you have the following:

- Basic understanding of command-line interface (CLI) tools
- Familiarity with Docker and its concepts (for deploying S2DS implementations)
- Python 3.9 or higher installed on your system

## 4.3 Installation

### Installation Steps

1. Download the Scistream package by clicking [here](../dist/scistream_proto-1.0.0-py3-none-any.whl).

2. Install the downloaded package using pip:

```bash
pip install scistream_proto-1.0.0-py3-none-any.whl
```

### Troubleshooting

- If you encounter permission issues related to Docker, consider adding your user to the Docker group by following the instructions in this tutorial: [Manage Docker as a non-root user.](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)


## 4.4 How SciStream Works

SciStream enables high-speed, memory-to-memory data streaming between scientific instruments and remote computing facilities. The process involves the following steps:

1. The user authenticates with the participating facilities and requests a streaming job through the SciStream User Client (S2UC).

2. The SciStream Control Servers (S2CS) at the producer and consumer facilities negotiate the connection details and allocate the necessary resources.

3. The SciStream Data Servers (S2DS) establish authenticated and transparent connections between the data producer and consumer.

4. The data producer streams data to the consumer through the SciStream infrastructure, enabling real-time analysis and visualization.

### Example Usage

Here's a real-world example of how SciStream can be used to stream data from a scientific instrument to a remote computing facility for real-time analysis and visualization.

1. Set up the microscope to produce high-resolution images and connect it to a local computing device running SciStream.

2. Configure a local iperf client to act as the data producer.

3. Set up a remote iperf server to act as data consumer at a remote to perform some type of analysis. Install SciStream on this facility and configure it as the data relay.

4. Use the SciStream User Client (S2UC) to authenticate with both the data producer facility and the remote computing facility, and then request a streaming job.

5. SciStream will establish a high-speed, memory-to-memory data streaming connection between the data producer and the remote computing facility.

## 4.5 Tutorial

### Authentication

SciStream integrates with the Globus platform to provide a secure and convenient authentication mechanism. Globus enables federated identity management, allowing users to access resources across different organizations using their institutional credentials. This is achieved through SSO and integration with institutional identity providers.

Let's start by clearing out the authentication tokens:

```
s2uc logout
```

Next, log in using the following command:

```
s2uc login --scope 1234
```

You will see a URL. Open the provided URL in a web browser, log in with the proper credentials, and then copy and paste the authorization code into the CLI prompt:

```
s2uc login --scope 1234
```

You should see the following output:

```
Please authenticate with Globus here:

------------------------------------
https://auth.globus.org/v2/oauth2/authorize?client_id=4787c84e-9c55-a11c&redirect_uri=https%3A%2F%2Fauth.globus.org=login
------------------------------------

Enter the resulting Authorization Code here:
```

After successfully logging in, you can proceed to the next step in the tutorial.

If the client is properly configured and you have followed the authentication steps above, everything should work as expected.

```
s2uc prod-req --mock True --scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5
```
```
uid; s2cs; access_token; role
localhost
b87c38b2-798f-11ee-9fa8-9801a78d65ff localhost:5000 Agxdy4EWwGr84HoNVdw PROD
waiting for hello message
started client request
req started, with request uid: "b87c38b2-798f-11ee-9fa8-9801a78d65ff"
role: "PROD"
num_conn: 5
rate: 10000

Added key: 'b87c38b2-798f-11ee-9fa8-9801a78d65ff' with entry: {'role': 'PROD', 'num_conn': 5, 'rate': 10000, 'hello_received': <threading.Event object at 0x10e81a3d0>, 'prod_listeners': []}
```
For more information on authentication and authorization, proceed to the Authentication Guide.

## 4.6 SciStream User Client (S2UC) Commands

The SciStream User Client (S2UC) is the command-line interface (CLI) tool that allows users to interact with S2CS. It provides various commands for authentication, request management, and stream control.

### 4.6.1 Usage

```bash
s2uc COMMAND [ARGS]...
```

#### Commands

#### `login`

Get Globus credentials for the SciStream User Client.

```bash
s2uc login [OPTIONS]
```

##### Options

- `--scope TEXT`: Specify the scope ID for which to obtain the credentials. Default is "c42c0dac-0a52-408e-a04f-5d31bfe0aef8".

#### `check_auth`

Display the Globus credentials for a given IP address or scope.

```bash
s2uc check_auth [OPTIONS]
```

##### Options

- `--ip TEXT`: Specify the IP address to fetch the scope and get the access token.
- `--scope TEXT`: Directly provide the scope ID to get the access token.

#### `logout`

Log out of Globus and remove all authentication tokens.

```bash
s2uc logout
```

#### `release`

Release a specific request identified by its unique ID (UID).

```bash
s2uc release [OPTIONS] UID
```

##### Arguments

- `UID`: The unique ID of the request to be released.

##### Options

- `--s2cs TEXT`: Specify the address of the SciStream Control Server (S2CS). Default is "localhost:5000".

#### `prod_req`

Initiate a producer request to the SciStream Control Server (S2CS).

```bash
s2uc prod_req [OPTIONS]
```

##### Options

- `--num_conn INTEGER`: Specify the number of connections. Default is 5.
- `--rate INTEGER`: Specify the rate of the request. Default is 10000.
- `--s2cs TEXT`: Specify the address of the SciStream Control Server (S2CS). Default is "localhost:5000".
- `--mock`: Use mock data for the request.
- `--scope TEXT`: Specify the scope ID for the request.

#### `cons_req`

Initiate a consumer request to the SciStream Control Server (S2CS).

```bash
s2uc cons_req [OPTIONS] UID PROD_LSTN
```

##### Arguments

- `UID`: The unique ID of the request.
- `PROD_LSTN`: The producer listener information.

##### Options

- `--num_conn INTEGER`: Specify the number of connections. Default is 5.
- `--rate INTEGER`: Specify the rate of the request. Default is 10000.
- `--s2cs TEXT`: Specify the address of the SciStream Control Server (S2CS). Default is "localhost:6000".
- `--scope TEXT`: Specify the scope ID for the request.

## Examples

### Login

```bash
s2uc login --scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
```

### Check Authentication

```bash
s2uc check_auth --ip 192.168.0.100
s2uc check_auth --scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
```

### Logout

```bash
s2uc logout
```

### Release

```bash
s2uc release 4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 --s2cs localhost:5000
```

### Producer Request

```bash
s2uc prod_req --num_conn 10 --rate 5000 --s2cs localhost:5000 --mock --scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
```

### Consumer Request

```bash
s2uc cons_req --num_conn 10 --rate 5000 --s2cs localhost:6000 --scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8 4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 192.168.0.100:8000
```

## 4.7 SciStream Control Server (S2CS) commands

### 4.7.1 Usage

```
s2cs --listener_ip=IP_ADDRESS --port=PORT_NUMBER --type=TYPE --v --verbose --client_id=CLIENT_ID --client_secret=CLIENT_SECRET --version
```

### 4.7.2 Parameters

```
--listener_ip: The reachable IP address on which s2cs will listen it's important to set this value accordingly. Default is '0.0.0.0'.
--port: The port number on which s2cs will listen. Default is 5000.
--type: The s2ds type. Default is 'Haproxy'.
--v: A flag to enable more verbosity.
--client_id: The client ID to be used for authentication. Default is None.
--client_secret: The client secret to be used for authentication. Default is None.
```
