# Scistream Client Authentication Workflow

Let's start from a clean slate by performing a logout:
```
(scistream-proto-py3.9) $ python src/s2uc.py logout
Successfully logged out!
```

## 1. Simple request with no credentials

#### 1a. Scistream Server Does Not Require Authentication (Default Case)

Notice this is the default behavior for the Scistream server, if we do not explicitly specify an authentication scope it will not require authentication. This is the command:
```
(scistream-proto-py3.9)$ python src/s2cs.py --verbose
Server started on 0.0.0.0:5000
```

The client sends the request without needing to login.

```
(scistream-proto-py3.9)$ python src/s2uc.py prod-req
uid; s2cs; access_token; role
3bca6862-78f3-11ee-90c6-9801a78d65ff localhost:5000 INVALID_TOKEN PROD
waiting for hello message
started client request
```
The server processes the request without any authentication error.
```
(scistream-proto-py3.9)$ python src/s2cs.py --verbose
Server started on 0.0.0.0:5000
req started, with request uid: "3bca6862-78f3-11ee-90c6-9801a78d65ff"
role: "PROD"
num_conn: 5
rate: 10000

Added key: '3bca6862-78f3-11ee-90c6-9801a78d65ff' with entry: {'role': 'PROD', 'num_conn': 5, 'rate': 10000, 'hello_received': <threading.Event object at 0x10ae8e370>, 'prod_listeners': []}
```

#### 1b. Server Requires Authentication - Failed

In this example we explictly specify a client secret, the client secret and client id is uniquely mapped to an authentication scope, and it will validate each request with globus and error on every request that is not authorized for this scope. Notice the server might take some time to start as it connects to Globus Auth. Example:
```
(scistream-proto-py3.9)$ python src/s2cs.py --client_secret="CONTACTUSFORTHIS" --verbose
Server started on 0.0.0.0:5000
```

Client command execution without credentials:
```
(scistream-proto-py3.9) $python src/s2uc.py prod-req
uid; s2cs; access_token; role
5b0aa168-78fa-11ee-9ad8-9801a78d65ff localhost:5000 INVALID_TOKEN PROD
waiting for hello message
started client request
Please obtain new credentials: Authentication token is invalid for scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
```
Server response/error indicating the need for authentication.
```
Authentication token is invalid for scope_id c42c0dac-0a52-408e-a04f-5d31bfe0aef8
Error in function 'req':
Traceback (most recent call last):
  File "/Users/flaviojr123/dev/argonne/scistream-proto/src/utils.py", line 38, in wrapper
    result = func(*args, **kwargs)
  File "/Users/flaviojr123/dev/argonne/scistream-proto/src/utils.py", line 69, in decorated_function
    context.abort(StatusCode.UNAUTHENTICATED, f'Authentication token is invalid for scope {self.client_id}')
  File "/Users/flaviojr123/Library/Caches/pypoetry/virtualenvs/scistream-proto-pXNK2Vat-py3.9/lib/python3.9/site-packages/grpc/_server.py", line 404, in abort
    raise Exception()
Exception

req took 0.0009 seconds
```
## 2. Successful Login and Credential Verification

#### 2a. User logs into an existing scope


```
(scistream-proto-py3.9)$ python src/s2uc.py login --scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
To obtain token for the scope, please open the URL in your browser and follow the instructions
Please authenticate with Globus here:
------------------------------------
https://auth.globus.org/v2/oauth2/authorize?client_id=4787c84e-9c55-4881-b941-cb6720cea11c&redirect_uri=https%3A%2F%2Fauth.globus.org%2Fv2%2Fweb%2Fauth-code&scope=https%3A%2F%2Fauth.globus.org%2Fscopes%2Fc42c0dac-0a52-408e-a04f-5d31bfe0aef8%2Fscistream&state=_default&response_type=code&code_challenge=lN6qHOyfH9t-D689XoVrCdjUS8RaBvyOZkOBaAuVpmM&code_challenge_method=S256&access_type=offline&prompt=login
------------------------------------

Enter the resulting Authorization Code here:
```
After log in the user can then verify it's local credentials:

```
(scistream-proto-py3.9)$ python src/s2uc.py check-auth
Access Token for scope 'c42c0dac-0a52-408e-a04f-5d31bfe0aef8': Agxdy4EWykel6d1r84HoNVdw
```

#### 2b. Server Requires Authentication - Failed due to IP lookup

In this example we explictly specify an authentication scope, and it will validate each request with globus and error on every request that is not authorized for this scope. Example:
```
(scistream-proto-py3.9)$ python src/s2cs.py --client_secret="CONTACTUSFORTHIS"
```

**Expected Behavior**:
  - The client sends request, but the client is not configured correctly
  - The server throws an error indicating that it requires authentication.

Notice that in the client request there's a lookup in a configuration file, we get the scope_id from the ip in the s2cs.

```
def get_scope_id(s2cs):
    scope_map={
        "10.16.42.61": "c42c0dac-0a52-408e-a04f-5d31bfe0aef8",
        "10.16.41.12": "c42c0dac-0a52-408e-a04f-5d31bfe0aef8",
        "10.16.42.31": "c42c0dac-0a52-408e-a04f-5d31bfe0aef8"
    }
    ip = s2cs.split(":")[0]
    return scope_map.get(ip, "")
    ## When IP is not found error silently, maybe not desirable
```

Client command execution without credentials:
```
(scistream-proto-py3.9) $python src/s2uc.py prod-req
uid; s2cs; access_token; role
5b0aa168-78fa-11ee-9ad8-9801a78d65ff localhost:5000 INVALID_TOKEN PROD
waiting for hello message
started client request
Please obtain new credentials: Authentication token is invalid for scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
```
Server response/error indicating the need for authentication.
```
Authentication token is invalid for scope_id c42c0dac-0a52-408e-a04f-5d31bfe0aef8
Error in function 'req':
Traceback (most recent call last):
  File "/Users/flaviojr123/dev/argonne/scistream-proto/src/utils.py", line 38, in wrapper
    result = func(*args, **kwargs)
  File "/Users/flaviojr123/dev/argonne/scistream-proto/src/utils.py", line 69, in decorated_function
    context.abort(StatusCode.UNAUTHENTICATED, f'Authentication token is invalid for scope {self.client_id}')
  File "/Users/flaviojr123/Library/Caches/pypoetry/virtualenvs/scistream-proto-pXNK2Vat-py3.9/lib/python3.9/site-packages/grpc/_server.py", line 404, in abort
    raise Exception()
Exception

req took 0.0009 seconds
```

#### 2d. Server Requires Authentication - Success

To configure this modify the s2uc file:

```
def get_scope_id(s2cs):
    scope_map={
        "10.16.42.61": "c42c0dac-0a52-408e-a04f-5d31bfe0aef8",
        "10.16.41.12": "c42c0dac-0a52-408e-a04f-5d31bfe0aef8",
        "10.16.42.31": "c42c0dac-0a52-408e-a04f-5d31bfe0aef8",
        "localhost": "c42c0dac-0a52-408e-a04f-5d31bfe0aef8"
    }
    ip = s2cs.split(":")[0]
    return scope_map.get(ip, "")
```


If the client is properly configured and we follow the steps above, then everything should work.

```
(scistream-proto-py3.9) $python src/s2uc.py prod-req
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
(scistream-proto-py3.9)$ python src/s2cs.py --client_id="26c25f3c-c4b7-4107-8a25-df96898a24fe" --client_secret="="
```
(Note: The server is expecting authentication for a particular scope_ID)

**Client Command**:
```
(scistream-proto-py3.9) $python src/s2uc.py prod-req
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
python src/s2uc.py login --scope 26c25f3c-c4b7-4107-8a25-df96898a24fe

```
Both credentials can be visualized using the appropriate CLI command.

```
python src/s2uc.py check-auth --scope 26c25f3c-c4b7-4107-8a25-df96898a24fe
Access Token for scope '26c25f3c-c4b7-4107-8a25-df96898a24fe': AgV3ezP
python src/s2uc.py check-auth
Access Token for scope 'c42c0dac-0a52-408e-a04f-5d31bfe0aef8': Agxdy4E
```
---

#### 5. Sending Commands to Multiple Servers Post Multi-Scope Login

Following a successful multi-scope login, the client sends commands to servers associated with both scopes.

Server Setup for the First Scope:
```
python src/s2cs.py --client_id="26c25f3c-c4b7-4107-8a25-df96898a24fe" --client_secret="=" --listener-ip=10.0.0.1
```

Server Setup for the Second Scope:
```
python src/s2cs.py --client_id="ca7207c4-c1fd-482f-916d-7997c6e05de2" --client_secret="=" --listener-ip=10.0.0.2
```

Client Command to Send to the First Server:
```
python src/s2uc.py prod-req --s2cs 10.0.0.1:5000
```

Client Command to Send to the Second Server:
```
python src/s2uc.py prod-req --s2cs 10.0.0.2:5000
```
Scope map:

```
scope_map={
    "10.0.0.1": "26c25f3c-c4b7-4107-8a25-df96898a24fe",
    "10.0.0.2": "ca7207c4-c1fd-482f-916d-7997c6e05de2",
}
```
**Expected Behavior**:
  - Commands sent to both servers (each associated with different scopes) execute successfully.

**Screenshots Required**:
  - Successful command execution on the first server.
  - Successful command execution on the second server.
