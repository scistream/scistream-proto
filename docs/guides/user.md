# User Guide

### Software components
* **SciStream Data Server (S2DS):** software that runs on gateway nodes.

* **SciStream User Client (S2UC):** software that the end user and/or workflow engines/tools acting on behalf of the user interact with and provide relevant information to orchestrate end-to-end data streaming.
* **SciStream Control Server (S2CS):** a software running on one of the gateway nodes. It interacts with S2UC, data producer/consumer and S2DS. Orchestrates S2DS.

### Installation

The easiest way is to install using pip. To install from the source code please check our [developer guide.](../guides/dev.md)

#### Dependencies

We tested it for python 3.9+. We require docker for deploying the Haproxy and Nginx implementations for S2DS.

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
