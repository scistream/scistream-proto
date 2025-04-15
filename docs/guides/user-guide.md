# 5. SciStream User Guide

## 5.1 Overview

SciStream is an open source streaming facility API for registering services and mapping them to external IP addresses and ports with a secure data plane connection. It enables a zero-trust security model for scientific data transfer between facilities. SciStream is currently deployed at Advanced Photon Source (APS) and Argonne Leadership Computing Facility (ALCF) with ongoing discussions for deployment at other facilities.

## 5.2 Use Cases

This guide covers two primary user experiences:

1. **HPC Service Deployment**: Configuring an inbound proxy at an HPC facility to various components
2. **Instrument Connection**: Establishing an outbound proxy from a scientific instrument to securely transmit data to an HPC

## 5.3 Key Components

As a user, you'll interact with these components:

- **SciStream User Client (S2UC)**: Command-line tool for creating and managing connections
- **SciStream Control Server (S2CS)**: Running at each endpoint, manages connection setup
- **SciStream Data Server (S2DS)**: Handles the actual data transfer (runs automatically)

## 5.4 Use Case 1: Deploying a Service at HPC

When you want to offer a service from an HPC facility:

### 5.4.1 Configure the Inbound Proxy

```bash
s2uc inbound_request --s2cs hpc.facility.org:5000 --remote_ip 10.0.1.5 --receiver_ports 5001
```

This registers your service with SciStream and creates an inbound proxy that accepts secure connections from remote instruments.

The command returns:
- A unique identifier (UID)
- A listener address

Share these details with the instrument operators who need to connect to your service.

### 5.4.2 Start Your Service

Ensure your service is running and listening on the specified receiver port:

```bash
# Example: Start a data reconstruction service
reconstruction_service --listen 5001

```

## 5.5 Use Case 2: Connecting an Instrument to HPC

When you need to connect an instrument to use a service at an HPC facility:

### 5.5.1 Obtain Connection Details

Get the UID and listener address from the HPC service operator.

### 5.5.2 Configure the Outbound Proxy

```bash
s2uc outbound_request --s2cs instrument.facility.org:5000 --remote_ip 192.168.2.10 --receiver_ports 5100 YOUR_UID HPC_LISTENER_ADDRESS
```

This establishes a secure tunnel between your instrument and the HPC service.

### 5.5.3 Connect Your Instrument

Configure your data source software to send data to the local proxy port:

```bash
# Example: Configure beamline data source
beamline_source --output localhost:5100
```

Data sent to this port will be securely transmitted to the HPC service.

## 5.6 Authentication

For secured endpoints (recommended in production):

```bash
s2uc login --scope YOUR_SCOPE_ID
s2uc check-auth --scope YOUR_SCOPE_ID  # Verify authentication
```

## 5.7 Releasing Resources

When finished with a connection:

```bash
s2uc release YOUR_UID --s2cs server.facility.org:5000
```

## 5.8 Common Options

- `--num_conn`: Number of parallel connections (default: 5)
- `--rate`: Maximum data rate in kb/s (default: 10000)
- `--server_cert`: Path to SSL certificate for secure connections
- `--scope`: Authentication scope ID for secured endpoints

## 5.9 Next Steps

For detailed examples and advanced configurations, see the [Tutorials](tutorials.md) section.
