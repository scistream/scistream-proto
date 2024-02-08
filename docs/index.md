# Index

Scistream enables high-speed memory-to-memory
 data streaming in scientific environments.

 We have a python implementation and a deployment solution compatible with docker and kubernetes.

If you want to learn more about Scistream, please take a look at our [HPDC'22 paper](https://dl.acm.org/doi/abs/10.1145/3502181.3531475).

## Documentation

   - [Getting started](quickstart.md)
   - [User Guide](user-guide/README.md)
   - [Developer Guide](dev-guide/README.md)
   - [Benchmarks](benchmarks/README.md)
   - [About](about/README.md)

## Project layout

    poetry.lock         # Explicitly documents all Python dependencies using Poetry
    pyproject.toml      # Python dependencie: Poetry equivalent to requirements.txt
    mkdocs.yml          # Documentation configuration file.
    docs/
      index.md          # The documentation homepage.
      ...               # Other markdown pages, images and other files.
    deploy/
      setup.sh          # Installation script
    src/
      proto/            # GRPC protocol specifications
      appcontroller.py  # Application controller reference implementations
      s2cs.py           # Scistream Control Server implementation
      s2ds.py           # Scistream Dataplane server plugin
      s2uc.py           # Scistream User Client implementation
      utils.py          # Supporting code
      ...               # other files
    tests/
      test_s2cs.py      # pytest tests
      ...               # other tests

### Service
      The protocol should enable high-speed, memory-to-memory data streaming in scientific environments
      by establishing streaming data channels between two remote facilities using our reference architecture:

      ![alt text](figures/simple-arch.png "SciStream architecture")

      Buffer-and-forward elements are run at the Science DMZ to create bridges between the Ethernet-based WAN and HPC interconnets where data producers/consumers may reside.

### Software components
      * **SciStream Data Server (S2DS):** software that runs on gateway nodes. It acts as a buffer-and-forward agent.
      * **SciStream User Client (S2UC):** software that the end user and/or workflow engines/tools acting on behalf of the user interact with and provide relevant information (e.g., ID of a HPC job, ID of an experiment or data acquisition job on a scientific instrument, shared secret for secure communication with the user job (application) at the producer and consumer) to orchestrate end-to-end data streaming.
      * **SciStream Control Server (S2CS):** a software running on one of the gateway nodes. It interacts with S2UC, data producer/consumer and S2DS.

### Environment
      * S2UC communicates with producer/consumer S2CS over a private LAN/WAN or the Internet
      * S2CS and S2DS communicate over a LAN
      * Messages can be lost or corrupted

### Vocabulary of Messages
      * **Requests:** { REQ, ReqListeners }
      * **Responses:** { RESP, ProdLstn }
      * **Commands:** { StartLstn, Hello, UpdateTargets, StartConn, Connect, REL }

### Procedure Rules (Informal)
      0. The user selects producer and consumer facilities, and authenticates with them via S2UC.
      1. S2UC establishes an authenticated connection to (both producer and consumer) S2CS, and sends the “user request” (REQ) for the streaming job (which contains unique-id, protocol, number of connections, streaming rate, producer address and consumer address)
      2. S2CS requests num_conn ports from S2DS, whom reserves num_conn ports on gateway nodes depending on availability
      3. Both producer and consumer S2CS send connection information (i.e., IP addresses and ports) for data connections to S2UC
      4. When ProdApp starts, it connects to producer S2CS and presents the “unique-id” and set of port listeners
      5. Prod S2CS forwards set of port listeners to S2UC
      6. S2UC creates connection map and data connection credentials, and sends them to both producer and consumer S2CS
      7. Both producer and consumer S2DS create bridges between Prod/Cons App and the WAN (i.e., start buffer-and-forward elements)
      8. ConsApp establishes num_conn data streaming channels
      9. Both S2DS use data connection credentials to establish external (WAN) streaming channel
      10. ProdApp starts streaming task

### Collaboration Diagram

      ![alt text](figures/collaboration-diagram.png "SciStream collaboration diagram")

### Sequence Diagram

      ![alt text](figures/scistream-protocol-simple.png "SciStream sequence diagram")
