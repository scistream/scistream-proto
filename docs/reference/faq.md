# Frequently Asked Questions

## Integration and Outreach

### How do I get help integrating with SciStream?

If you have a science use case requiring real-time analysis or secure streaming, or you have a streaming application you'd like to integrate with the SciStream control protocol, please contact us. You can also integrate if you have a data plane component that wants to use SciStream as its northbound API.

Please email our mailing list at scistream at anl dot gov with details about your use case or integration needs.

### Can I integrate my streaming application with SciStream?

Yes! SciStream is designed to work with existing streaming applications. There are several integration approaches:

1. **Use SciStream as a tunnel**: The simplest approach is to use SciStream to create a secure tunnel for your existing application without modifying the application code.

2. **Integrate with the SciStream control protocol**: For deeper integration, you can build support for the SciStream control protocol directly into your application, allowing it to dynamically establish and manage connections.

3. **Use SciStream as a northbound API**: If you're developing a data plane component, you can use SciStream as its control interface, leveraging the authentication, authorization, and connection management features.

For detailed integration guidance, please contact our team at scistream at anl dot gov.

### What scientific applications are suitable for SciStream?

SciStream is particularly well-suited for:

- Real-time data analysis from scientific instruments
- Remote visualization of experiment data
- Streaming data from detectors to HPC facilities
- Secure multi-facility workflows
- Any application requiring secure, high-performance data transfer between facilities

## General Questions

### What is SciStream?

SciStream is a security framework enabling protected, high-speed data streaming between scientific instruments and high-performance computing (HPC) facilities. It provides a zero-trust security model with flexible deployment options across institutions.

### Where is SciStream currently deployed?

SciStream is currently deployed at the Advanced Photon Source (APS) and Argonne Leadership Computing Facility (ALCF), with ongoing discussions for deployment at other research facilities.

### Is SciStream open source?

Yes, SciStream is open source software. You can find the source code on [GitHub](https://github.com/scistream/scistream-proto).

## Setting Up Data Transfer

### Do I need my own streaming application to use SciStream?

Yes, you need your own streaming application. SciStream provides the secure tunnel between endpoints, but you need applications that:
1. Generate data on the producer side
2. Consume data on the consumer side

SciStream doesn't include these applications - it facilitates secure communication between your existing applications.

### How can I demonstrate data flow through SciStream?

You can demonstrate data flow using iperf3, a standard network performance tool:

#### Using iperf3:

On the producer machine (behind the inbound proxy):
```bash
iperf3 -s -p 5074  # Use the port you configured in your inbound request
```

On the consumer machine (behind the outbound proxy):
```bash
iperf3 -c localhost -p 5100  # Use the port you configured in your outbound request
```

This will show data flowing through the SciStream tunnel with throughput statistics.

### Where should I point client and server IPs for stream flow?

- **Producer application**: Should listen on the port specified in your inbound request's `--receiver_ports` (e.g., 5074)
- **Consumer application**: Should connect to `localhost` (or 127.0.0.1) on the port specified in your outbound request's `--receiver_ports` (e.g., 5100)

This setup allows the consumer application to connect to the local port, which SciStream then securely forwards to the producer application.

## Technical Questions

### What types of traffic does SciStream support?

SciStream supports several types of network traffic:

- **TCP**: Basic TCP traffic forwarding (not secure by itself)
- **UDP**: Datagram-based communication (not secure by itself)
- **TLS/SSL**: Encrypted TCP traffic (recommended for secure communication)

While SciStream can forward both UDP and unencrypted TCP traffic, using TLS/SSL encryption is highly recommended for security-sensitive applications. The secure data plane provided by SciStream adds an additional layer of protection.

### Why am I seeing "INVALID_TOKEN" in the output?

Don't be concerned - this is not an error. The `INVALID_TOKEN` text is simply a placeholder used when authentication is disabled, such as in development environments. It indicates you're running in an unauthenticated mode, which is acceptable for testing but not recommended for production.

In future versions, this will be renamed to a less concerning term like "NO_AUTH" or "DEV_MODE".

### What is the difference between inbound and outbound requests?

- **Inbound request**: Sets up the receiving end of the tunnel (server side). This registers a service that will receive data.
- **Outbound request**: Sets up the sending end of the tunnel (client side). This connects to an inbound service and establishes the data channel.

### Can I use SciStream in Docker/Kubernetes environments?

Yes, SciStream works well in containerized environments. The components can run in Docker containers or Kubernetes pods. When deploying in these environments:

- Ensure network connectivity between pods/containers
- Use appropriate port mappings
- Mount volume for certificates if needed
- Consider using the host network for optimal performance

### What are common port numbers used by SciStream?

- 5000: Default S2CS control server port
- 5100-5105: Common data channel ports
- You can configure custom port ranges using the `--port-range` option

## Terminology

### Is there confusing terminology in SciStream?

Yes, some current terminology can be confusing:

| Current Term | What It Actually Means | Better Alternative |
|--------------|------------------------|-------------------|
| `prod_listeners` | Destination endpoints where data is sent | "destinations" or "targets" |
| `listeners` | Entry points that accept connections | "service ports" or "entry points" |
| `Client request` | Initial session establishment | "Session Init" |
| `Hello Request` | Registration of connection endpoints | "Session Request" |

Future versions of SciStream may adopt clearer terminology.

## Additional Help

For troubleshooting common issues such as:
- Certificate validation problems
- Installation errors
- Process cleanup
- Connection debugging

Please refer to the [Troubleshooting Guide](troubleshooting.md) or contact us at scistream at anl dot gov.