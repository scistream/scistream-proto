# 5. Authentication and Security

In this page, we will cover how SciStream integrates with the Globus platform for control channel authentication, how to configure authentication settings, and how to secure your data streams. We will also discuss access control mechanisms and best practices for ensuring the security of your SciStream environment.

We expect you to have reviewed all the previous chapters:

- [1. Introduction](../introduction.md)
- [2. Understanding SciStream](../scistream.md)
- [3. Getting Started](../quickstart.md)
- [4. User Guide](user.md)

## 5.1 Globus Auth

SciStream integrates with Globus for authentication and authorization purposes. This integration enables federated identity management, allowing users from different institutions to authenticate using their existing credentials. Globus Auth acts as a trusted identity provider, securely storing user information and providing a standardized interface for authentication and authorization.

The use of OAuth 2.0 in Globus Auth allows users to grant SciStream access to their resources without sharing their credentials directly. Instead, access tokens are issued by Globus Auth after the user authenticates and consents to the requested permissions. This approach enhances security and simplifies user management, as there is no need to create and manage separate user accounts for SciStream across multiple institutions.

For further information check the Globus Auth [docs](https://docs.globus.org/api/auth/)

## 5.2 Prerequisites
Before proceeding with the authentication and security configuration, ensure
that you have the following:

- A Globus account: If you don't have one, you can create a Globus account at [https://www.globus.org/signup](https://www.globus.org/signup).
- SciStream installed on your system
- Basic understanding of authentication and authorization concepts.

## 5.3 Configuring Authentication

To enable authentication in SciStream, you need to perform the following steps:

### 5.3.1 Obtain Globus Auth configuration credentials:
1. Log in to the Globus Developer Portal at [https://developers.globus.org/](https://developers.globus.org/).
2. Create a new project and register a new app.
3. Note down the Client ID and Client Secret for your app.
5. Configure the app to restrict authentication to a specific domain, such as Argonne National Laboratory. This ensures that only users from the specified domain can authenticate and access the SciStream resources associated with this app.

### 5.3.2 Configure the SciStream Control Server (S2CS):
1. Start the S2CS with the appropriate command-line options, specifying the Client ID and Client Secret obtained from Globus Auth.

```
s2cs -t Haproxy --verbose --client_id="YOUR_CLIENT_ID" --client_secret="YOUR_CLIENT_SECRET"
```

If no client_id and client_secret are provided to S2CS, it will not require authentication.

### 5.3.3 User login and credential management in the SciStream User Client (S2UC):
1. Run the login command to prompt the user to authenticate with Globus and obtain an access token for a specific scope.

    ```
    s2uc login --scope YOUR_SCOPE_ID
    ```

2. The access token will be securely stored for future requests.
3. To clear the stored credentials, run the logout command.

```
s2uc logout
```

### 5.3.4 Include the access token in requests to S2CS:
1. When sending requests to S2CS using S2UC, include the access token and the scope ID.

```
s2uc prod-req --mock True --scope YOUR_SCOPE_ID
```

### 5.3.5 Access control in S2CS:

1. S2CS will verify the validity and scope of the access token using the Globus Auth API.
2. Based on the token's permissions, S2CS will grant or deny access to the requested resources.



## 5.4 Authentication Scenarios

SciStream supports various authentication scenarios to cater to different use cases and requirements. Let's explore these scenarios in detail:

### 5.4.1 Successful Request with No Credentials
By default, if no authentication scope is explicitly specified, SciStream Control Server (S2CS) will not require authentication. Here's an example:

- Start the S2CS without specifying any client ID or secret:

```
s2cs -t Haproxy --verbose
```
Output:

  ```
  Server started on 0.0.0.0:5000
  ```

- Send a request using the SciStream User Client (S2UC) without logging in:

```
s2uc prod-req --mock True
```
Output:
```
  uid; s2cs; access_token; role
  4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 localhost:5000 INVALID_TOKEN PROD
  waiting for hello message
  started client request
```
- The server processes the request without any authentication error:

```
  req started, with request uid: "4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3"
  role: "PROD"
  num_conn: 5
  rate: 10000

  Added key: '4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3' with entry: {'role': 'PROD', 'num_conn': 5, 'rate': 10000, 'hello_received': <threading.Event object at 0x10ae8e370>, 'prod_listeners': []}
```

### 5.4.2 Failed Request when Server Requires Authentication
In this scenario, the S2CS is configured with a client ID and secret, indicating that it requires authentication. If the client sends a request without providing valid credentials, the request will fail.

- Start the S2CS with a client ID and secret:

```
s2cs -t Haproxy --verbose --client_id="INFO_ID" --client_secret="CONTACTUSFORTHIS"
```

  Server started on 0.0.0.0:5000

- Send a request using S2UC without logging in:

```
s2uc prod-req --mock True
```
Output:
```
  uid; s2cs; access_token; role
  storage.db
  4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 localhost:5000 INVALID_TOKEN PROD
  waiting for hello message
  started client request
  Please obtain new credentials: Authentication token is invalid for scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5q
```
- The server responds with an authentication error:

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

### 5.4.3 Successful Request with Valid Credentials
When the S2CS requires authentication, the client must provide valid credentials to successfully send a request.

- Log in to Globus using S2UC:

```
$ s2uc login --scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
```
Output:
```
  To obtain token for the scope, please open the URL in your browser and follow the instructions
  Please authenticate with Globus here:
  ------------------------------------
  https://auth.globus.org/v2/oauth...
  ------------------------------------
  Enter the resulting Authorization Code here:
```
- Verify the obtained credentials:

```
s2uc check-auth --scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5
```
Output:
```
  Access Token for scope '92c36fec-6d3c-41f6-a487-dfda1281c4e5: Agxdy4EWykel6d1r84HoNVdw
```
- Send a request using S2UC with the valid credentials:

```
s2uc prod-req --mock True --scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5
```

```
  uid; s2cs; access_token; role
  localhost
  b87c38b2-798f-11ee-9fa8-9801a78d65ff localhost:5000 Agxdy4EWwGr84HoNVdw PROD
  waiting for hello message
  started client request
```
- The server processes the request successfully:

```
req started, with request uid: "b87c38b2-798f-11ee-9fa8-9801a78d65ff"
role: "PROD"
num_conn: 5
rate: 10000
Added key: 'b87c38b2-798f-11ee-9fa8-9801a78d65ff' with entry: {'role': 'PROD', 'num_conn': 5, 'rate': 10000, 'hello_received': <threading.Event object at 0x10e81a3d0>, 'prod_listeners': []}
```
### 5.4.4 Failed Request with Incorrect Credentials
If the client provides incorrect or invalid credentials, the request will fail.

- Start the S2CS with a specific client ID and secret:

```
s2cs -t Haproxy --verbose --client_id="26c25f3c-c4b7-4107-8a25-df96898a24fe" --client_secret="="
```

- Send a request using S2UC with credentials for a different scope:

```
s2uc prod-req --mock True --scope 92c36fec-6d3c-41f6-a487-dfda1281c4e5
```
```
  uid; s2cs; access_token; role
  localhost
  a692c5ac-7990-11ee-a79a-9801a78d65ff localhost:5000 Agxdy484HoNVdw PROD
  waiting for hello message
  started client request
  Please obtain new credentials: Authentication token is invalid for scope 26c25f3c-c4b7-4107-8a25-df96898a24fe
```
- The server responds with an authentication error:

```
Authentication token is invalid for scope_id 26c25f3c-c4b7-4107-8a25-df96898a24fe
```

### 5.4.5 Logging in and Sending Requests to Multiple Control Servers
SciStream allows clients to log in to multiple scopes and send requests to different control servers associated with those scopes.

- Log in to the first scope:

```
s2uc login --scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
```

- Log in to the second scope:

```
s2uc login --scope 26c25f3c-c4b7-4107-8a25-df96898a24fe
```

- Verify the obtained credentials for both scopes:

```
s2uc check-auth --scope 26c25f3c-c4b7-4107-8a25-df96898a24fe
```

- Send a request to the first S2CS:
```
s2uc prod-req --s2cs 10.0.0.1:5000 --scope c42c0dac-0a52-408e-a04f-5d31bfe0aef8
```

- Send a request to the second S2CS:
```
s2uc prod-req --s2cs 10.0.0.1:5000 --scope 26c25f3c-c4b7-4107-8a25-df96898a24fe
```

These scenarios demonstrate how SciStream handles different authentication requirements and allows clients to interact with multiple control servers using separate scopes.
