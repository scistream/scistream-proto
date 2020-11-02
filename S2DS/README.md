# SciStream Data Server (S2DS)

The S2DS provides the functionality of mapping between the WAN and LAN connections and to send, receive, and buffer streaming data when necessary.
We will use the asynchronous I/O mode to handle high speed store-and-forward for S2DS.
Each gateway node will have an S2DS initiator running with superuser privileges and listening on a predefined port.
It will be configured to accept connections only from local S2CS.
This initiator process will likely be launched with xinetd, a super-server daemon that manages network services.
S2DS initiator will start an S2DS process for each streaming request and will set the user identity of the process (via a mechanism like setuid) to the user.
