# 4. Getting Started with Scistream

A quick reference guide for setting up and running SciStream.

## 4.1 Prerequisites

- Docker
- Python 3.9+

## 4.2 Installation

```bash
# Using pip
pip install scistream-proto

# Using Docker
docker pull castroflaviojr/scistream:1.2.1
```

## 4.3 Starting the Control Server

```bash
# Start the SciStream Control Server
s2cs -t Haproxy --verbose

# With authentication (recommended for production)
s2cs -t Haproxy --verbose --client_id="YOUR_CLIENT_ID" --client_secret="YOUR_CLIENT_SECRET"
```

## 4.4 Creating Connection Requests

```bash
# Create inbound request (server side)
s2uc inbound_request --s2cs localhost:5000 --remote_ip 10.0.1.5 --receiver_ports 5001

# Create outbound request (client side)
s2uc outbound_request --s2cs localhost:5000 --remote_ip 192.168.2.10 --receiver_ports 5100 UID LISTENER_ADDRESS
```

## 4.5 Testing and Managing Connections

```bash
# Test an application (mock producer)
appctrl mock UID localhost:5000 TOKEN PROD 10.0.0.1

# Release a connection when done
s2uc release UID --s2cs localhost:5000

# Authentication commands
s2uc login --scope YOUR_SCOPE_ID
s2uc check-auth --scope YOUR_SCOPE_ID

# Run a test with iperf
# Server side
iperf -s -p 5001
# Client side
iperf -c localhost -p 5100 -t 60
```

For more detailed information and advanced usage, please refer to the complete [User Guide](../guides/user-guide.md).

## 4.6 Common Options

```bash
# With SSL certificate
--server_cert=path/to/cert.crt

# Multiple parallel connections
--num_conn=10

# Rate limiting
--rate=20000  # 20 MB/s
```
