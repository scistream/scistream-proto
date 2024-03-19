# Authentication Tutorial

## Exercise 1

Objective: Implement authentication and authorization features in the SciStream framework using Globus Auth.

Steps:

1. Set up a development environment with a SciStream Control Server (S2CS) and a SciStream User Client (S2UC).
2. Configure the S2CS to require authentication:
  - Obtain a client ID and client secret from Globus Auth.
  - Start the S2CS with the appropriate command-line options, specifying the client ID and client secret.
~~~
$ s2cs -t Haproxy --verbose --client_id="INFO_ID" --client_secret="CONTACTUSFORTHIS"
~~~
  - if no client_id and client_secret is provided to S2CS it will not require authentication.

3. User login and credential management in the S2UC:
  - Run a login command that prompts the user to authenticate with Globus and obtain an access token for a specific scope.
~~~
$ s2uc login --scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
~~~
  - Store the access token securely for future requests.
  - Run a logout command to clear the stored credentials.
~~~
$ s2uc logout
~~~

4. Run s2uc including the access token in request to S2CS:
~~~
s2uc prod-req --mock True --scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5
~~~
5. Access Control is then implemented in S2CS:

  - S2CS will verify the validity and scope of the access token using the Globus Auth API. This is implemented in the function "validate_creds()" if you would like to check the code itself.
  - It will grant or deny the request based on the token.

## Exercise 2:

Test Various authentications and authorization scenarios:

1. Successful request with no credentials
2. Failed request when no client credentials are provided but server requests credentials
3. Successfull when client provides credentials and server requires authentication
4. Failed request when incorrect credentials are provided
5. Logging in and sending requests to multiple control servers

To support federated identity management, we integrated with Globus Auth, which allows us to authenticate users from a diverse set of systems. As of now, we associate each entity with a scope_id.

Each SciStream Control Server is configured to use a specific scope_id. When a user makes a request, they need to meet the criteria specified in the scope and explicitly authorize the use of their credentials by that application. When making a request, the user must specify the scope_id of the control server. That's defined with the client_id.

Let's start from a clean slate by performing a logout:
```
$ s2uc logout
Successfully logged out!
```

### 1. Simple request with no credentials

Notice this is the default behavior for the Scistream server, if we do not explicitly specify an authentication scope, it will not require authentication. Here's the command:
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

### 2. Server Requires Authentication - Failed

In this example, we explicitly specify a client secret. The client secret and client ID are uniquely mapped to an authentication scope, and S2CS will validate each request with Globus and return an error for every request that is not authorized for this scope. Note that the server might take some time to start as it connects to Globus Auth.

Server setup:

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
### 3. Successful Login and Credential Verification

User logs into an existing scope:
```
$ s2uc login --scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
To obtain token for the scope, please open the URL in your browser and follow the instructions
Please authenticate with Globus here:
------------------------------------
https://auth.globus.org/v2/oauth2/authorize?client_id=4787c84e-9c55-4881-b941-cb6720cea11c&redirect_uri=https%3A%2F%2Fauth.globus.org%2Fv2%2Fweb%2Fauth-code&scope=https%3A%2F%2Fauth.globus.org%2Fscopes%2Fc42c0dac-0a52-408e-a04f-5d31bfe0aef8%2Fscistream&state=_default&response_type=code&code_challenge=lN6qHOyfH9t-D689XoVrCdjUS8RaBvyOZkOBaAuVpmM&code_challenge_method=S256&access_type=offline&prompt=login
------------------------------------

Enter the resulting Authorization Code here:
```
After logging in, the user can then verify their local credentials:

```
s2uc check-auth --scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5
Access Token for scope '92c36fec-6d3c-41f6-a487-dfda1281c4e5: Agxdy4EWykel6d1r84HoNVdw
```
If the client is properly configured and the above steps are followed, everything should work.

```
s2uc prod-req --mock True --scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5
uid; s2cs; access_token; role
localhost
b87c38b2-798f-11ee-9fa8-9801a78d65ff localhost:5000 Agxdy4EWwGr84HoNVdw PROD
waiting for hello message
started client request
```

Server response:

```
req started, with request uid: "b87c38b2-798f-11ee-9fa8-9801a78d65ff"
role: "PROD"
num_conn: 5
rate: 10000

Added key: 'b87c38b2-798f-11ee-9fa8-9801a78d65ff' with entry: {'role': 'PROD', 'num_conn': 5, 'rate': 10000, 'hello_received': <threading.Event object at 0x10e81a3d0>, 'prod_listeners': []}
```

### 4. Sending a Command without Relevant Credentials

In this scenario, the client tries to send a command to a server without having the required credentials for the server's scope.

Server setup (expecting authentication for a particular scope_id):

```
$ s2cs -t Haproxy --verbose --client_id="26c25f3c-c4b7-4107-8a25-df96898a24fe" --client_secret="="
```
Client command (attempting to execute without the required credentials for the server's scope):

```
s2uc prod-req --mock True --scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5
uid; s2cs; access_token; role
localhost
a692c5ac-7990-11ee-a79a-9801a78d65ff localhost:5000 Agxdy484HoNVdw PROD
waiting for hello message
started client request
Please obtain new credentials: Authentication token is invalid for scope 26c25f3c-c4b7-4107-8a25-df96898a24fe
```
Server response:
```
Authentication token is invalid for scope_id 26c25f3c-c4b7-4107-8a25-df96898a24fe
```
### 5. Logging in to a Second Scope

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

- If the request can't be authenticated make sure that your authentication token is up to date for the correct scope_id.

- Also ensure the request is using the correct scope
```
s2uc logout
s2uc login --scope abcdef
s2uc prod-req --scope abcdef
```

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
