import logging
import sys
import fire
import grpc
import threading

from .proto import scistream_pb2
from .proto import scistream_pb2_grpc

from concurrent import futures
from .s2ds.s2ds import create_instance
from .utils import request_decorator, set_verbosity, authenticated
from globus_action_provider_tools.authentication import TokenChecker


class S2CSException(Exception):
    pass


default_cid = "c42c0dac-0a52-408e-a04f-5d31bfe0aef8"
default_secret = ""
default_server_crt = "server.crt"
default_server_key = "server.key"

import importlib.metadata

__version__ = importlib.metadata.version("scistream-proto")


class S2CS(scistream_pb2_grpc.ControlServicer):
    TIMEOUT = 180  # timeout value in seconds

    def __init__(
        self,
        listener_ip,
        verbose,
        start_port=5100,
        end_port=5200,
        type="Haproxy",
        client_id=default_cid,
        client_secret=default_secret,
    ):
        self.response = None
        self.resource_map = {}
        self.listener_ip = listener_ip
        self.client_id = client_id
        self.client_secret = client_secret
        self.type = type
        self.start_port = start_port
        self.end_port= end_port
        self.used_ports=set()

        # Moving checker instantiation to the begginning, this was making the request take too long
        if self.client_secret != "":
            self.checker = TokenChecker(
                client_id=self.client_id,
                client_secret=self.client_secret,
                expected_scopes=[
                    f"https://auth.globus.org/scopes/{self.client_id}/scistream"
                ],
            )
        set_verbosity(self, verbose)
        self.logger.info(f"Starting S2CS server with type: {self.type}")

    # @validate_args(has=["role", "uid", "num_conn", "rate"])
    @request_decorator
    @authenticated
    def req(self, request: scistream_pb2.Request, context=None):
        self.resource_map[request.uid] = {
            "role": request.role,
            "num_conn": request.num_conn,
            "rate": request.rate,
            "hello_received": threading.Event(),
            "prod_listeners": [],
        }
        self.logger.debug(
            f"Added key: '{request.uid}' with entry: {self.resource_map[request.uid]}"
        )
        ##FIXTHIS start function should be the same for all implementations
        if self.type in ["StunnelSubprocess", "HaproxySubprocess"]:
            self.s2ds = create_instance(self.type, self.logger)
            ports = self.get_available_ports(request.num_conn)
            self.logger.debug(
                f"Available ports: {ports}"
            )
            reply = self.s2ds.start(request.num_conn, self.listener_ip, ports)
        else:
            self.s2ds = create_instance(self.type)
            reply = self.s2ds.start(request.num_conn, self.listener_ip)
        self.resource_map[request.uid].update(reply)
        ##DEBUG message here show resource map
        hello_received = self.resource_map[request.uid]["hello_received"].wait(
            S2CS.TIMEOUT
        )

        if not hello_received:
            self.release_request(request.uid)
            raise S2CSException(f"Hello not received within the timeout period")

        return self.response

    @request_decorator
    @authenticated
    def update(self, request, context=None):
        # improve validation
        listeners = request.remote_listeners
        ## remote listeners are the destination ports
        entry = self.resource_map[request.uid]
        print(request.role)
        if request.role == "PROD":
            ## inbound proxy
            listeners = [
                listeners[i % len(listeners)] for i in range(entry["num_conn"])
            ]
        else:
            ##outbound proxy
            # TODO write a test case for this
            listeners = [
                listeners[i % len(listeners)] for i in range(entry["num_conn"])
            ]
            entry["prods2cs_listeners"] = listeners
            # Include remote listeners for transparency to user
        self.s2ds.update_listeners(
            listeners, entry["s2ds_proc"], request.uid, request.role
        )
        self.logger.debug(
            f"Updated : '{request.uid}' with entry: {self.resource_map[request.uid]}"
        )
        response = scistream_pb2.Response(
            listeners=entry["listeners"], prod_listeners=listeners
        )
        return response

    @request_decorator
    @authenticated
    def release(self, request, context=None):
        self.release_request(request.uid)
        response = scistream_pb2.Response()
        return response

    # Release all resources used by a particular request
    def release_request(self, uid):
        removed_item = self.resource_map.pop(uid, None)
        self.s2ds.release(removed_item)
        self.logger.debug(f"Removed key: '{uid}' with entry: {removed_item}")

    def release_all(self):
        self.logger.info("Releasing all resources")
        uids = [i for i in self.resource_map]
        for i in uids:
            self.release_request(i)

    @authenticated
    @request_decorator
    def hello(self, request, context=None):
        ## Possible race condition here between REQ and HELLO
        entry = self.resource_map[request.uid]
        if request.role == "PROD":
            ## Producer equals INBOUND proxy
            ## entry listeners equals INBOUND ports
            ## prod_listeners are the INTERNAL destination ports
            ## resource map data structure is not very inteligible
            entry["prod_listeners"] = request.prod_listeners
            self.response = scistream_pb2.Response(
                listeners=entry["listeners"], prod_listeners=entry["prod_listeners"]
            )
            AppResponse = scistream_pb2.AppResponse(message="Sending Prod listeners...")
            print("receiving ports")
            print(entry["listeners"])
            print("target ports")
            print(entry["prod_listeners"])
            print("DEBUG HERE")
            print(self.response)
        else:
            ## Consumer equals OUTBOUND proxy
            ## entry listeners equals OUTBOUND ports
            ## Missing destination ports in this case
            self.response = scistream_pb2.Response(listeners=entry["listeners"])
            print(entry["listeners"])
            print("DEBUG HERE")
            AppResponse = scistream_pb2.AppResponse(
                message="Sending listeners...", listeners=entry["listeners"]
            )
        entry["hello_received"].set()
        return AppResponse

    def validate_creds(self, access_token):
        auth_state = self.checker.check_token(access_token)
        return len(auth_state.identities) > 0
        # return False
    
    def get_available_ports(self, num_conn):
        ## Given port range tuple, given used ports set
        ## returns the first n ports available using sequential allocation strategy.
        ## until num_connections
        available = []
        self.logger.debug(
                f"Port_range: {self.start_port, self.end_port}"
            )
        self.logger.debug(
                f"Used_ports: {self.start_port, self.end_port}"
            )
        for port in range(self.start_port, self.end_port +1):
            if port not in self.used_ports:
                available.append(port)
                if len(available) == num_conn:
                    break
        self.used_ports.update(available)
        return available


def start(
    listener_ip="0.0.0.0",
    port=5000,
    port_range = "5100-5200",
    type="S2DS",
    v=False,
    verbose=False,
    client_id=default_cid,
    client_secret=default_secret,
    version=False,
    server_crt=default_server_crt,
    server_key=default_server_key,
):
    """
    Starts a gRPC implementation of Scistream server.

    Args:
        listener_ip (str): IP address on which the control server listens. Defaults to '0.0.0.0'.
        port (int): Control Channel port number on which the gRPC server listens. Defaults to 5000.
        port_range: Hyphenated string specifying the port range for S2DS. Defaults to "5100-5200"
        type (str): Specifies the type of server to start. Options are 'S2DS', 'Nginx', 'Haproxy', 'StunnelSubprocess'.
                    'Haproxy' is the default type.
        v or verbose (bool): Enables detailed logging and debug output . Defaults to False.
        client_id (str): Client ID for Globus Auth. Defaults to value of 'default_cid'.
        client_secret (str): Client secret for Globus Auth. Defaults to value of 'default_secret'.
        version (bool): Prints the version of the package.
        server_crt (str): Path to the SSL/TLS certificate file. Defaults to 'server.crt'.
        server_key (str): Path to the server key file. Defaults to 'server.key'.
    """

    ## Better input validation will provide better error messages
    if version:
        print(f"s2cs, version: {__version__}")
        return
    with open(server_key, "rb") as f:
        private_key = f.read()
    with open(server_crt, "rb") as f:
        certificate_chain = f.read()
    if "-" not in port_range:
        raise ValueError("port_range must be hyphenated")
    start_port, end_port = port_range.split("-")
    if int(start_port) > int(end_port):
        raise ValueError("Start port must be less than or equal to end port")
    server_credentials = grpc.ssl_server_credentials([(private_key, certificate_chain)])
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        servicer = S2CS( listener_ip = listener_ip,
                         verbose = (v or verbose), 
                         type = type, 
                         client_id = client_id, 
                         client_secret = client_secret, 
                         start_port = int(start_port), 
                         end_port = int(end_port))
        scistream_pb2_grpc.add_ControlServicer_to_server(servicer, server)
        server.add_secure_port(f"[::]:{port}", server_credentials)
        server.start()
        print(f"Secure Server started on {listener_ip}:{port}")
        server.wait_for_termination()
    except KeyboardInterrupt:
        servicer.release_all()
        print("\nTerminating server")
        sys.exit(0)


def main():
    fire.Fire(start)


if __name__ == "__main__":
    main()
