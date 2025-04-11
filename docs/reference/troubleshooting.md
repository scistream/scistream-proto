# 7. Troubleshooting Guide

This guide helps you solve common issues with SciStream and clarifies potentially confusing terminology.

## 7.1 Understanding SciStream Terminology

SciStream uses several technical terms that might be unclear. Here's what they actually mean:

### 7.1.1 Current Terms and Their Meaning

| Current Term | What It Actually Means | Better Alternative |
|--------------|------------------------|-------------------|
| `prod_listeners` | Destination endpoints where data is sent | "destinations" or "targets" |
| `listeners` | Entry points that accept connections | "service ports" or "entry points" |
| `INVALID_TOKEN` | Default placeholder when auth is disabled | "NO_AUTH" or "DEV_MODE" |
| `Client request` | Initial session establishment | "Session Init" |
| `Hello Request` | Registration of connection endpoints | "Session Request" or "Session Registration" |

> Note: These alternative terms are recommendations for future versions. Current SciStream code still uses the original terminology.

### 7.1.2 Example of Confusing Output and Its Meaning

When you see output like:
```
uid; s2cs; access_token; role
bd9f1a7e-04d7-11f0-b44c-946dae415862 192.168.10.11:5000 INVALID_TOKEN PROD
```

What this actually means:
- A session has been initialized with ID `bd9f1a7e-04d7-11f0-b44c-946dae415862`
- It's connecting to the control server at `192.168.10.11:5000`
- Authentication is disabled (thus the `INVALID_TOKEN` placeholder)
- This is setting up the producer side of the connection

Don't be alarmed by `INVALID_TOKEN` - it's just indicating you're in development mode without authentication.

## 7.2 SSL/TLS Certificate Issues

### 7.2.1 SSL Certificate Errors During Development

**Problem:** Certificate validation errors during development.

**Solution:** Use the `--ssl=False` flag when starting S2CS to disable strict certificate validation:
```bash
s2cs --type=Haproxy --ssl=False
```

### 7.2.2 Certificate Management Best Practices

**For Development:**
- Use self-signed certificates with appropriate Subject Alternative Names (SANs)
- Disable strict validation with `--ssl=False`
   
**For Production:**
- Use properly signed certificates from a trusted CA
- Enable strict validation (default)
- Regularly rotate certificates before expiration

### 7.2.3 Generating Certificates for Development

```bash
# Create a configuration file
cat > cert.conf << EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = YOUR_IP_ADDRESS

[v3_req]
subjectAltName = IP:YOUR_IP_ADDRESS
EOF

# Generate the certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -config cert.conf
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt -extfile cert.conf -extensions v3_req
```

Replace `YOUR_IP_ADDRESS` with the actual IP address of your server.

## 7.3 Common Issues and Solutions

### 7.3.1 Connection Errors

**Issue: "Cannot connect to control server"**

Solution:
- Verify S2CS is running: `ps -ef | grep s2cs`
- Check port accessibility: `telnet <s2cs_ip> 5000`
- Confirm network connectivity between machines

**Issue: "Error during update: [Errno 2] No such file or directory: 'haproxy'"**

Solution:
- Install the missing proxy software:
  ```bash
  sudo apt-get update && sudo apt-get install haproxy
  ```
- Restart the S2CS service

### 7.3.2 Port Conflicts

**Issue: "Address already in use"**

Solution:
- Check for existing services: `ss -tlpn | grep <port>`
- Kill conflicting processes or choose a different port
- Clean up old processes if using the subprocess implementation:
  ```bash
  ps -ef | grep "haproxy\|stunnel\|nginx" && kill <PID>
  ```

### 7.3.3 Authentication Problems

**Issue: "Authentication token is invalid for scope..."**

Solution:
- Verify your scope: `s2uc check-auth --scope <scope_id>`
- Re-authenticate: `s2uc login --scope <scope_id>`
- Ensure S2CS is configured with the correct client ID

### 7.3.4 Data Flow Issues

**Issue: "Data not flowing through the tunnel"**

Solution:
- Verify tunnel establishment: `ss -tlpn | grep <port>`
- Ensure your application connects to the correct port
- Test with iperf3:
  ```bash
  # Server side
  iperf3 -s -p <receiver_port>
  
  # Client side
  iperf3 -c localhost -p <local_port>
  ```

**Issue: Proxy processes remain after stopping S2CS**

Solution:
- Find and terminate orphaned processes:
  ```bash
  ps -ef | grep "haproxy\|stunnel\|nginx" && kill <PID>
  ```

## 7.4 Logging and Debugging

Enable verbose logging:
```bash
s2cs --verbose --type=Haproxy
```

Check proxy logs:
```bash
cat ~/.scistream/<uid>.conf  # View configuration
cat ~/.scistream/<uid>.log   # View logs
```

## 7.5 Getting Additional Help

If still experiencing issues:

- Collect diagnostic information:
  ```bash
  s2uc --version
  ps -ef | grep s2
  ss -tlpn
  ```

- Create an issue on [GitHub](https://github.com/scistream/scistream-proto/issues) with:
  - Steps to reproduce
  - Expected vs. actual behavior
  - Debug information
  - Environment details (OS, deployment method)