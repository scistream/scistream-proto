# Quickstart
## SciStream Control Protocol
The SciStream protocol attempts to tackle the problem of enabling high-speed,
memory-to-memory data streaming in scientific environments.
This task is particularly challenging because data producers
(e.g., data acquisition applications on scientific instruments, simulations on supercomputers)
and consumers (e.g., data analysis applications) may be in different security domains
(and thus require bridging of those domains).
Furthermore, either producers, consumers, or both may lack external network connectivity (and thus require traffic forwarding proxies).
If you want to learn more, please take a look at our [HPDC'22 paper](https://dl.acm.org/doi/abs/10.1145/3502181.3531475).

## Pre-requisites
We use [poetry](https://python-poetry.org/docs/) to manage our python environments. Please ensure you have Python 3.9+ and poetry installed in your environment. We require docker for using the Haproxy and NGINX S2DS implementation. We provide a setup scrit that was used to install these dependencies on the Fabric platform. This installation script was tested on ubuntu 20.04 version.

We also use a Git submodules to manage dependencies, such as the original S2DS implementation project. To set up the SciStream Data Server (S2DS) submodule, run the following commands:

~~~
git submodule init
git submodule update
cd scistream/S2DS
make
cd ../../
~~~

This process initializes, updates, and compiles the submodule, streamlining your project setup and ensuring compatibility with the latest version of the parent project.


## Quick Start

Once you have the dependencies the following commands download and installs all the necessary python dependencies. It also activates the virtual environment.

~~~
poetry install
poetry shell
~~~~

The easiest way to verify if the code works is to run pytest:

~~~
poetry run pytest
~~~

The output of the test should look like this:

~~~
========================================== test session starts ==========================================
platform linux -- Python 3.9.16, pytest-7.2.2, pluggy-1.0.0
rootdir: /home/fcastro/dev/scistream-proto
plugins: timeout-2.1.0
collected 6 items                                                                                       

tests/test_s2cs.py .x....                                                                         [100%]

===================================== 5 passed, 1 xfailed in 5.81s ======================================
~~~

Once this runs all the
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

### Running scistream

To understand the behavior of the code let's simulate the environment by opening 3 terminals, 1 for the s2cs Producer, 1 for s2cs Consumer, and one for the client terminal.

To run this you will need to open multiple terminals:

~~~
python src/s2cs.py --port=5000 --listener-ip=10.133.137.2 --verbose --type=Haproxy
python src/s2uc.py prod-req --s2cs 10.133.137.2:5000

python src/appcontroller.py create-appctrl cac92bb0-7345-11ee-9876-bff742c41932 10.130.134.2:5000 AgpQoBo1VvvYkz8yYxyQgkgrW7nobYmG6dno8q8rgKG9MMYDM2IvCjgEezy8mqJpqvMl44GDq5GKayTyvkXn4fdmoB2 PROD 10.133.139.2

python src/s2uc.py cons-req --s2cs 10.130.134.2:5000 cac92bb0-7345-11ee-9876-bff742c41932 10.133.137.2:5001

python src/appcontroller.py create-appctrl cac92bb0-7345-11ee-9876-bff742c41932 10.130.134.2:5000 AgpQoBo1VvvYkz8yYxyQgkgrW7nobYmG6dno8q8rgKG9MMYDM2IvCjgEezy8mqJpqvMl44GDq5GKayTyvkXn4fdmoB2 CONS 10.130.133.2
~~~

Several things will happen in the background to learn more please review the code. The output of the client should look like this:

~~~
listeners: "0.0.0.0:43579"
listeners: "0.0.0.0:34375"
listeners: "0.0.0.0:34343"
listeners: "0.0.0.0:38223"
listeners: "0.0.0.0:34865"
prod_listeners: "127.0.0.1:7000"
prod_listeners: "127.0.0.1:17000"
prod_listeners: "127.0.0.1:27000"
prod_listeners: "127.0.0.1:37000"
prod_listeners: "127.0.0.1:47000"

Sending updated connection map information...
82f0e9b8-eb7d-11ed-be3c-f303ca66dd31
~~~
In this case 82f0e9b8-eb7d-11ed-be3c-f303ca66dd31 is the uid, let's use that to send a release:
~~~
$ python src/s2uc.py release 82f0e9b8-eb7d-11ed-be3c-f303ca66dd31
Release completed
~~~
## Troubleshooting Guide

The first step of troubleshooting is restarting everything with the --verbose flag:
~~~
python src/s2cs.py start --port=5000 --listener-ip=127.0.0.1 --verbose
~~~

This should output more info, if you continue facing issues please create an issue on github.

## FAQ

Make sure that you start the poetry environment with the correct python version

## Specification

## Authentication

How to create scopes:

CLIENT_ID="92c36fec-6d3c-41f6-a487-dfda1281c4e5"
CLIENT_SECRET="oDU3/7WgwFU8nAX+Mtsnb4X6UeHBv7KJsA37U1xw6XQ="

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
