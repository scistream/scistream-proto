# Troubleshooting Guide

This guide helps you solve common issues with SciStream and clarifies potentially confusing terminology.

## Understanding SciStream Terminology

SciStream uses several technical terms that might be unclear. Here's what they actually mean:

### Current Terms and Their Meaning

| Current Term | What It Actually Means | Better Alternative |
|--------------|------------------------|-------------------|
| `prod_listeners` | Destination endpoints where data is sent | "destinations" or "targets" |
| `listeners` | Entry points that accept connections | "service ports" or "entry points" |
| `INVALID_TOKEN` | Default placeholder when auth is disabled | "NO_AUTH" or "DEV_MODE" |
| `Client request` | Initial session establishment | "Session Init" |
| `Hello Request` | Registration of connection endpoints | "Session Request" or "Session Registration" |

> Note: These alternative terms are recommendations for future versions. Current SciStream code still uses the original terminology.

### Example of Confusing Output and Its Meaning

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

## SSL/TLS Certificate Issues

### Issue: SSL Certificate Errors During Development

Certificate validation errors can be frustrating during development. SciStream provides an `--ssl` flag to control certificate behavior in the control plane.

**Solution for development environments:**

Use the `--ssl=False` flag when starting S2CS to disable strict certificate validation:

```bash
s2cs --type=Haproxy --ssl=False
```

This uses `grpc.ssl_server_credentials([(private_key, None)])` which relaxes certificate requirements.

### Best Practices for Certificate Management

1. **For Development:**
   - Use self-signed certificates with appropriate Subject Alternative Names (SANs)
   - Disable strict validation with `--ssl=False`
   
2. **For Production:**
   - Use properly signed certificates from a trusted CA
   - Enable strict validation (default)
   - Regularly rotate certificates before expiration

### Generating Valid Certificates for Development

Create certificates with proper SANs:

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

## Common Issues and Solutions

### Connection Errors

#### Issue: "Cannot connect to control server"

**Solution:**
1. Verify that the S2CS service is running: `ps -ef | grep s2cs`
2. Check that the port is accessible: `telnet <s2cs_ip> 5000`
3. Ensure proper network connectivity between machines

#### Issue: "Error during update: [Errno 2] No such file or directory: 'haproxy'"

**Solution:**
1. Install the missing proxy software:
   ```bash
   sudo apt-get update
   sudo apt-get install haproxy
   ```
2. Restart the S2CS service

### Port Conflicts

#### Issue: "Address already in use"

**Solution:**
1. Check for existing services using that port: `ss -tlpn | grep <port>`
2. Kill conflicting processes or choose a different port
3. If using the subprocess implementation, clean up old processes:
   ```bash
   ps -ef | grep "haproxy\|stunnel\|nginx"
   kill <PID>
   ```

### Authentication Problems

#### Issue: "Authentication token is invalid for scope..."

**Solution:**
1. Verify you're using the correct scope: `s2uc check-auth --scope <scope_id>`
2. Re-authenticate if needed: `s2uc login --scope <scope_id>`
3. Ensure the S2CS is configured with the correct client ID

### Data Flow Issues

#### Issue: "Data not flowing through the tunnel"

**Solution:**
1. Verify the tunnel is established correctly:
   ```bash
   ss -tlpn | grep <port>
   ```
2. Check your application is connecting to the correct port
3. Test with a simple tool like iperf3:
   ```bash
   # Server side
   iperf3 -s -p <receiver_port>
   
   # Client side
   iperf3 -c localhost -p <local_port>
   ```

#### Issue: Proxy processes remain after stopping S2CS

**Solution:**
1. Find orphaned processes:
   ```bash
   ps -ef | grep "haproxy\|stunnel\|nginx"
   ```
2. Terminate them manually:
   ```bash
   kill <PID>
   ```

## Logging and Debugging

### Enabling Verbose Logging

Start S2CS with the `--verbose` flag to get more detailed logs:

```bash
s2cs --verbose --type=Haproxy
```

### Checking Proxy Logs

For subprocess implementations, check the configuration directory:

```bash
cat ~/.scistream/<uid>.conf  # View proxy configuration
cat ~/.scistream/<uid>.log   # View proxy logs
```

## Getting Additional Help

If you're still experiencing issues, please:

1. Gather debug information:
   ```bash
   s2uc --version
   ps -ef | grep s2
   ss -tlpn
   ```

2. Create an issue on [GitHub](https://github.com/scistream/scistream-proto/issues) with:
   - Steps to reproduce
   - Expected vs. actual behavior
   - Debug information
   - Environment details (OS, deployment method)