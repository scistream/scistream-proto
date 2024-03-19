## Tutorial

### Installation

[Click here to download Scistream](dist/scistream_latest.whl)

~~~
pip install scistream_proto-0.1.5-py3-none-any.whl
~~~

### Start Control server

~~~
$ s2cs -t Haproxy --verbose
Server started on 0.0.0.0:5000
~~~

### Send request using Scistream Client

After that let's send a request:

~~~
$ s2uc prod-req --mock True
uid; s2cs; access_token; role
4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 localhost:5000 INVALID_TOKEN PROD
waiting for hello message
started client request
~~~

### Run Application controller mock
~~~
$ appctrl mock 4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3 localhost:5000 INVALID_TOKEN PROD 10.0.0.1
~~~
### release

~~~
s2uc release 4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3
~~~
For further details please check the complete user guide
