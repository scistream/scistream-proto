# User Guide

## How SciStream Works

1. The user authenticates with the participating facilities and requests a streaming job through the SciStream User Client (S2UC).
2. The SciStream Control Servers (S2CS) at the producer and consumer facilities negotiate the connection details and allocate the necessary resources.
3. The SciStream Data Servers (S2DS) establish authenticated and transparent connections between the data producer and consumer.
4. The data producer streams data to the consumer through the SciStream infrastructure, enabling real-time analysis and visualization.

### Installation

The easiest way is to install using pip. To install from the source code please check our [developer guide.](../guides/dev.md)

#### Dependencies

We tested it for python 3.9+. We require docker for deploying the Haproxy and Nginx implementations for S2DS.

## Tutorial

### Authentication

We integrated with globus platform for the purpose of authentication.

If your token expired you might want to start by logging out.
~~~
$ s2uc logout
~~~

After that let's log in:

~~~
$ s2uc login --scope 1234
~~~

You will see a URL. You need to open the url provided in a web browser, log in with the proper credentials, then copy and paste the authorization code into the cli prompt.

~~~
(scistream-proto-py3.9) bash-3.2$ s2uc login --scope 1234
Please authenticate with Globus here:
```------------------------------------
https://auth.globus.org/v2/oauth2/authorize?client_id=4787c84e-9c55-a11c&redirect_uri=https%3A%2F%2Fauth.globus.org=login
------------------------------------```

Enter the resulting Authorization Code here:
~~~

After logging in you can move to the next tutorial step.

### Example of usage

If the client is properly configured and we follow the steps above, then everything should work.

```
s2uc prod-req --mock True --scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5
uid; s2cs; access_token; role
localhost
b87c38b2-798f-11ee-9fa8-9801a78d65ff localhost:5000 Agxdy4EWwGr84HoNVdw PROD
waiting for hello message
started client request
```

```
req started, with request uid: "b87c38b2-798f-11ee-9fa8-9801a78d65ff"
role: "PROD"
num_conn: 5
rate: 10000

Added key: 'b87c38b2-798f-11ee-9fa8-9801a78d65ff' with entry: {'role': 'PROD', 'num_conn': 5, 'rate': 10000, 'hello_received': <threading.Event object at 0x10e81a3d0>, 'prod_listeners': []}
```

Proceed to the [Authentication Guide](auth.md)
