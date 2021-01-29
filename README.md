# SciStream Control Protocol

## Motivation
The SciStream protocol attempts to tackle the problem of enabling high-speed,
memory-to-memory data streaming in scientific environments.
This task is particularly challenging because data producers
(e.g., data acquisition applications on scientific instruments, simulations on supercomputers)
and consumers (e.g., data analysis applications) may be in different security domains
(and thus require bridging of those domains).
Furthermore, either producers, consumers, or both may lack external network connectivity (and thus require traffic forwarding proxies).

## Specification

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
* **Requests:** { UserReq, ProdReq, ConsReq, ReqExtListeners, ReqIntListeners }
* **Responses:** { ACK, Response, ERR, ProdListeners, ConsListeners, Update, StatusUpdate }
* **Commands:** { Hello, StartS2DS, StopS2DS, StartConn, Connect, ReadyToStream, StopStreaming, Terminate, ProdRel, ConsRel }

### Message Format
* UserReq (String unique_id, String protocol, uint32 num_conn, float rate, String prod_addr, String cons_addr)
* ProdReq (String unique_id, String protocol, uint32 num_conn, float rate)
* ConsReq (String unique_id, String protocol, uint32 num_conn, float rate)
* ReqExtListeners (uint_32 num_conn, float rate)
* ReqIntListeners (uint_32 num_conn, float rate)
* ACK ()
* ERR (String message)
* Response (Array[num_conn] tuple(String ip_addr, uint32 port))
* ProdExtListeners (Array[num_conn] tuple(String ip_addr, uint32 port))
* ProdIntListeners (Array[num_conn] tuple(String ip_addr, uint32 port))
* ConsIntListeners (Array[num_conn] tuple(String ip_addr, uint32 port))
* ConsExtConnectors (Array[num_conn] tuple(String ip_addr, uint32 port))
* Update (String unique_id, Dictionary conn_map, String data_conn_key)
* StatusUpdate (String message)
* Hello (String unique_id, [Array[num_conn] tuple(String ip_addr, uint32 port)])
* StartS2DS (String unique_id, Dictionary conn_map, String data_conn_key)
* StopS2DS (String unique_id, Dictionary conn_map)
* StartConn (Array[num_conn] tuple(String ip_addr, uint32 port))
* Connect ([String data_conn_key])
* ReadyToStream ()
* StopStreaming ()
* Terminate ()
* ProdRel (String unique_id)
* ConsRel (String unique_id)

### Procedure Rules (Informal)
1. The user selects producer and consumer facilities, and authenticates with them via S2UC.
2. S2UC establishes an authenticated connection to (both producer and consumer) S2CS, and sends the “user request” for the streaming job (which contains unique-id, protocol, number of connections, producer address and consumer address)
3. When ProdApp starts, it connects to producer S2CS and presents the “unique-id” and set of port listeners
4. If unique-id is valid, S2CS requests num_conn ports from S2DS, whom reserves num_conn ports on gateway nodes depending on availability
5. Both producer and consumer S2CS send connection information (i.e., IP addresses and ports) for data connections to S2UC
6. S2UC creates connection map and data connection credentials, and sends them to both producer and consumer S2CS
7. Both producer and consumer S2DS create bridges between Prod/Cons App and the WAN
8. ConsApp establishes num_conn data streaming channels
9. Both S2DS use data connection credentials to establish external (WAN) streaming channel
10. ProdApp starts streaming task

### Sequence Diagram

![alt text](figures/scistream-protocol-simple.png "SciStream sequence diagram")
