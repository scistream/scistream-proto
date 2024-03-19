# Auth

Right now, In the authentication we support the following features:

1. Successful request with no credentials
2. Failed request when no client credentials are provided but server requests credentials
3. Successfull when client provides credentials and server requires authentication
4. Client provides credentials but failed due to IP lookup
5. Failed request when incorrect credentials are provided
6. Logging in and sending requests to multiple control servers

The commands used and outputs are described below.

To support authentication to a federated system we integrated with Globus Auth. It allows us to authenticate users from a diverse set of systems. As of now we associate each entity with a scope_id.

Each Scistream Control server will then be configured to use a specific scope_id. When a user makes a request the user needs to meet the criteria specified in the scope and then must explicitly authorize the use of it's credentials by that application. When making a request the user must specify the scope_id of the control server.

## Scistream Client Authentication Workflow

Let's start from a clean slate by performing a logout:
```
$ s2uc logout
Successfully logged out!
```

## 1. Simple request with no credentials

#### 1a. Scistream Server Does Not Require Authentication (Default Case)

Notice this is the default behavior for the Scistream server, if we do not explicitly specify an authentication scope it will not require authentication. This is the command:
```
$ s2cs -t Haproxy --verbose
Server started on 0.0.0.0:5000
```

The client sends the request without needing to login.

```
$ s2uc prod-req --mock True
uid; s2cs; access_token; role
4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 localhost:5000 INVALID_TOKEN PROD
waiting for hello message
started client request
```
The server processes the request without any authentication error.
```
$ s2cs -t Haproxy --verbose
Server started on 0.0.0.0:5000
req started, with request uid: "4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3"
role: "PROD"
num_conn: 5
rate: 10000

Added key: '4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3' with entry: {'role': 'PROD', 'num_conn': 5, 'rate': 10000, 'hello_received': <threading.Event object at 0x10ae8e370>, 'prod_listeners': []}
```

#### 1b. Server Requires Authentication - Failed

In this example we explictly specify a client secret, the client secret and client id is uniquely mapped to an authentication scope, and it will validate each request with globus and error on every request that is not authorized for this scope. Notice the server might take some time to start as it connects to Globus Auth. Example:
```
$ s2cs -t Haproxy --verbose --client_id="INFO_ID" --client_secret="CONTACTUSFORTHIS"
Server started on 0.0.0.0:5000
```

Client command execution without credentials:
```
$ s2uc prod-req --mock True
uid; s2cs; access_token; role
storage.db
4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 localhost:5000 INVALID_TOKEN PROD
waiting for hello message
started client request
Please obtain new credentials: Authentication token is invalid for scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5q
```
Server response/error indicating the need for authentication.
```
Authentication token is invalid for scope_id 92c36fec-6d3c-41f6-a487-dfda1281c4e5
Error in function 'req':
Traceback (most recent call last):
  File "/home/vagrant/.cache/pypoetry/virtualenvs/vagrant-SMvzaRao-py3.10/lib/python3.10/site-packages/src/utils.py", line 43, in wrapper
    result = func(*args, **kwargs)
  File "/home/vagrant/.cache/pypoetry/virtualenvs/vagrant-SMvzaRao-py3.10/lib/python3.10/site-packages/src/utils.py", line 74, in decorated_function
    context.abort(StatusCode.UNAUTHENTICATED, f'Authentication token is invalid for scope {self.client_id}')
  File "/home/vagrant/.cache/pypoetry/virtualenvs/vagrant-SMvzaRao-py3.10/lib/python3.10/site-packages/grpc/_server.py", line 407, in abort
    raise Exception()
Exception

req took 0.0009 seconds
```
## 2. Successful Login and Credential Verification

#### 2a. User logs into an existing scope


```
$ s2uc login --scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
To obtain token for the scope, please open the URL in your browser and follow the instructions
Please authenticate with Globus here:
------------------------------------
https://auth.globus.org/v2/oauth2/authorize?client_id=4787c84e-9c55-4881-b941-cb6720cea11c&redirect_uri=https%3A%2F%2Fauth.globus.org%2Fv2%2Fweb%2Fauth-code&scope=https%3A%2F%2Fauth.globus.org%2Fscopes%2Fc42c0dac-0a52-408e-a04f-5d31bfe0aef8%2Fscistream&state=_default&response_type=code&code_challenge=lN6qHOyfH9t-D689XoVrCdjUS8RaBvyOZkOBaAuVpmM&code_challenge_method=S256&access_type=offline&prompt=login
------------------------------------

Enter the resulting Authorization Code here:
```
After log in the user can then verify it's local credentials:

```
s2uc check-auth --scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5
Access Token for scope '92c36fec-6d3c-41f6-a487-dfda1281c4e5: Agxdy4EWykel6d1r84HoNVdw
```

#### 2d. Server Requires Authentication - Success

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

#### 3. Sending a Command without Relevant Credentials

In this scenario, the client tries to send a command to a server without having the required credentials for the server's scope.

**Server Setup**:
```
$ s2cs -t Haproxy --verbose --client_id="26c25f3c-c4b7-4107-8a25-df96898a24fe" --client_secret="="
```
(Note: The server is expecting authentication for a particular scope_ID)

**Client Command**:
```
s2uc prod-req --mock True --scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5
uid; s2cs; access_token; role
localhost
a692c5ac-7990-11ee-a79a-9801a78d65ff localhost:5000 Agxdy484HoNVdw PROD
waiting for hello message
started client request
Please obtain new credentials: Authentication token is invalid for scope 26c25f3c-c4b7-4107-8a25-df96898a24fe
```
(Note: The client is attempting to execute a command without the required credentials for the server's scope)
```
Authentication token is invalid for scope_id 26c25f3c-c4b7-4107-8a25-df96898a24fe
```
**Expected Behavior**:
  - The error provides instructions on how to obtain the necessary credentials.
  - A remote error from the server is received, along with instructions.

#### 4. Logging in to a Second Scope

In this scenario, after having logged in to one scope, the client attempts to log in to a second, different scope.

The client attempts to log in to the second scope:
```
s2uc login --scope 26c25f3c-c4b7-4107-8a25-df96898a24fe

```
Both credentials can be visualized using the appropriate CLI command.

```
s2uc check-auth --scope 26c25f3c-c4b7-4107-8a25-df96898a24fe
Access Token for scope '26c25f3c-c4b7-4107-8a25-df96898a24fe': AgV3ezP
s2uc check-auth
Access Token for scope 'c42c0dac-0a52-408e-a04f-5d31bfe0aef8': Agxdy4E
```
---

#### 5. Sending Commands to Multiple Servers Post Multi-Scope Login

Following a successful multi-scope login, the client sends commands to servers associated with both scopes.

Server Setup for the First Scope:
```
s2cs --client_id="26c25f3c-c4b7-4107-8a25-df96898a24fe" --client_secret="=" --listener-ip=10.0.0.1
```

Server Setup for the Second Scope:
```
s2cs --client_id="ca7207c4-c1fd-482f-916d-7997c6e05de2" --client_secret="=" --listener-ip=10.0.0.2
```

Client Command to Send to the First Server:
```
s2uc prod-req --s2cs 10.0.0.1:5000
```

Client Command to Send to the Second Server:
```
s2uc prod-req --s2cs 10.0.0.2:5000
```

### FAQ

If the request can't be authenticated make sure that your authentication token is up to date for the correct scope_id. Also make sure the request is using the correct scope

s2uc logout
s2uc login --scope abcdef
"s2uc prod-req --scope abcdef"
is different than
"s2uc prod-req"

## Scope configuration

To create a scope we must use the globus auth API. Here is an example of how to do so.

curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -H \
    'Content-Type: application/json' \
    -X POST https://auth.globus.org/v2/api/clients/$CLIENT_ID/scopes \
    -d '{
        "scope": {
            "name": "Scistream Operations",
            "description": "All Operations on Scistream",
            "scope_suffix": "scistream",
            "dependent_scopes": [
                    {
                        "optional": false,
                        "requires_refresh_token": true,
                        "scope": "73320ffe-4cb4-4b25-a0a3-83d53d59ce4f"
                    }
                ],
            "advertised": false,
            "allow_refresh_tokens": true
        }
    }' | jq
