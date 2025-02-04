# SciStream Setup and Configuration Guide

## Overview
This guide describes the process of setting up and configuring SciStream for secure data streaming on Polaris at ALCF.

## Prerequisites
- Access to Polaris at ALCF
- Basic knowledge of SSH and terminal commands
- SciStream container access

## Step 1: Initial Connection and Container Setup
1. Connect to Polaris:
```bash
ssh polaris.alcf.anl.gov
```

2. Load required modules:
```bash
ml use /soft/modulefiles
ml load spack-pe-base/0.8.1
ml load apptainer
```

3. Launch the SciStream container:
```bash
apptainer shell scistream2.sif
```

4. Verify network configuration:
```bash
ip a | grep bond
```

## Step 2: SSL Certificate Generation
Generate a self-signed SSL certificate for secure communication:

```bash
openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout server.key -out server.crt \
    -subj "/CN=10.140.56.125" \
    -addext "subjectAltName=IP:10.140.56.125"
```

## Step 3: Start SciStream Server
Launch the SciStream server with the following configuration:

```bash
s2cs \
    --server_crt="scistream/server.crt" \
    --server_key="scistream/server.key" \
    --type="StunnelSubprocess" \
    --verbose \
    --listener_ip=10.140.56.125
```

## Step 4: Configure Client Connection
In a new terminal, set up the client connection:

```bash
s2uc inbound-request \
    --server_cert="scistream/server.crt" \
    --remote_ip 10.140.56.125 \
    --s2cs 10.140.56.125:5000 \
    --receiver_ports 9100 \
    --num_conn 1

```

## Step 5: Login Node Configuration
1. Request an interactive job:
```bash
qsub -I -l select=1 -l filesystems=home:eagle -l walltime=1:00:00 -q debug
```

2. Load modules and launch container:
```bash
ml use /soft/modulefiles
ml load spack-pe-base/0.8.1
ml load apptainer
apptainer shell scistream2.sif
```

3. Verify network configuration:
```bash
ip a | grep bond
```

## Step 6: Stunnel Configuration
Create a stunnel configuration file with the following contents:

```ini
; Stunnel Configuration
; Global Options
fips = no
PSKsecrets = /home/fcastro/.scistream/2d512072-e32e-11ef-9670-6805cae0353e.key
securityLevel = 0
debug = 7
foreground = yes
sslVersionMax = TLSv1.2
pid = /home/fcastro/.scistream/compute.pid

; PSK Client Configuration
[5100]
client = yes
accept = 5100
connect = 10.140.56.125:5100
ciphers = eNULL
```

## PBS Script
Here's a PBS script that includes the stunnel configuration:

```bash
#!/bin/bash
#PBS -N scistream_job
#PBS -l select=1
#PBS -l filesystems=home:eagle
#PBS -l walltime=1:00:00
#PBS -q debug

# Load required modules
ml use /soft/modulefiles
ml load spack-pe-base/0.8.1
ml load apptainer

# Create stunnel config directory if it doesn't exist
mkdir -p ~/.scistream

# Create stunnel configuration file
cat > ~/.scistream/stunnel.conf << 'EOL'
; Stunnel Configuration
; Global Options
fips = no
PSKsecrets = /home/fcastro/.scistream/2d512072-e32e-11ef-9670-6805cae0353e.key
securityLevel = 0
debug = 7
foreground = yes
sslVersionMax = TLSv1.2
pid = /home/fcastro/.scistream/compute.pid

; PSK Client Configuration
[5100]
client = yes
accept = 5100
connect = 10.140.56.125:5100
ciphers = eNULL
EOL

# Launch SciStream container and start stunnel
apptainer exec scistream2.sif stunnel ~/.scistream/stunnel.conf

# Wait for stunnel to initialize
sleep 5

# Your additional commands here
# The service will be available locally on port 5100

