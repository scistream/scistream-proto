import logging
import fire
import grpc
import sys
import threading
import scistream_pb2
import scistream_pb2_grpc
import models

from s2ds import S2DS
from itertools import cycle, islice
from concurrent import futures
from models import S2CSException

logging.basicConfig(level=logging.DEBUG)
#grpc_logger = logging.getLogger("grpc")
#grpc_logger.setLevel(logging.DEBUG)

class S2CS(scistream_pb2_grpc.ControlServicer):
    TIMEOUT = 180 #timeout value in seconds
    def __init__(self, listener_ip, verbose):
        self.response = None
        self.resource_map = {}
        self.listener_ip = listener_ip
        self.set_verbosity(verbose)

    def set_verbosity(self, verbose):
        #grpc_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        self.logger = logging.getLogger(__name__)
        #handler = logging.StreamHandler(sys.stdout)
        self.logger.setLevel(logging.DEBUG)
        #handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        #handler.setFormatter(formatter)
        #self.logger.addHandler(handler)

    #@validate_args(has=["role", "uid", "num_conn", "rate"])
    def req(self, request: scistream_pb2.Request, context):
        self.logger.info("Client Request Received")
        #models.validate_request(request)
        uid = request.uid
        if self.resource_map.get(uid):
            raise S2CSException("Entry already found for uid")
        self.resource_map[uid] = {
            "role": request.role,
            "num_conn": request.num_conn,
            "rate": request.rate,
            "hello_received": threading.Event()
        }
        self.logger.debug(f"Added key: '{uid}' with entry: {self.resource_map[uid]}")
        self.s2ds= S2DS()
        reply = self.s2ds.start(request.num_conn, self.listener_ip)
        self.resource_map[uid].update(reply)

        hello_received = self.resource_map[uid]['hello_received'].wait(S2CS.TIMEOUT)

        if not hello_received:
            self.release_request(uid)
            raise S2CSException(f"Hello not received within the timeout period")
        else:
            self.logger.info("Resources reserved")
            self.logger.debug(f"S2DS subprocess(es) reserved listeners: {self.resource_map[uid]['listeners']}")
            self.logger.debug(f"{self.response}")

        return self.response

    def update(self, request, context):
        self.logger.info(f"Targets updated for uid {request.uid}")
        if request.uid not in self.resource_map:
            raise S2CSException(f"Attempting to update nonexistent entry with key '{request.uid}'" )
        entry = self.resource_map[request.uid]
        #models.validate_update(request, entry)
        if (entry["role"] == "PROD"):
            if len(request.remote_listeners) < entry["num_conn"]:
                request.remote_listeners = list(islice(cycle(request.remote_listeners), entry["num_conn"]))
        else:
            entry["prods2cs_listeners"] = request.remote_listeners  # Include remote listeners for transparency to user
        # Send remote port information to S2DS subprocesses in format "remote_ip:remote_port\n"
        for i in range(len(request.remote_listeners)):
            curr_proc = entry["s2ds_proc"][i]
            curr_remote_conn = request.remote_listeners[i] + "\n"
            if curr_proc.poll() is not None:
                raise S2CSException(f"S2DS subprocess with PID '{curr_proc.pid}' unexpectedly quit")
            curr_proc.stdin.write(curr_remote_conn.encode())
            curr_proc.stdin.flush()
            self.logger.info(f"S2DS subprocess establishing connection with {curr_remote_conn.strip()}...")
        self.logger.info("Targets updated")
        response = scistream_pb2.Response(listeners=entry["listeners"], prod_listeners=request.remote_listeners)
        return response

    def release(self, request, context):
        self.logger.debug(f"Releasing S2DS resources for uid{request.uid}")
        #models.validate_uid(request)
        self.release_request(request.uid)
        response = scistream_pb2.Response(message="Resources released")
        self.logger.info("Released S2DS resources")
        return response

    # Release all resources used by a particular request
    def release_request(self, uid):
        if uid not in self.resource_map:
            raise S2CSException("Attempting to release unexistent uid")
        removed_item = self.resource_map.pop(uid, None)
        self.s2ds.release(removed_item)
        self.logger.debug(f"Removed key: '{uid}' with entry: {removed_item}")

    def hello(self, request,context):
        self.logger.debug(f"Hello request received for uid{request.uid}")
        #models.validate_uid(request)
        uid=request.uid
        if uid not in self.resource_map:
            raise S2CSException("Attempting to update unexistent uid")
        ## Possible race condition here between REQ and HELLO
        entry = self.resource_map[uid]
        if entry["role"] == "PROD":

            entry["prod_listeners"] = request.prod_listeners
            self.logger.debug("Received Prod listeners: %s" % entry["prod_listeners"])
            self.logger.debug(f"{entry.keys()}")
            self.response = scistream_pb2.Response(
                listeners = entry["listeners"],
                prod_listeners = entry["prod_listeners"]
            )
            AppResponse = scistream_pb2.AppResponse(message="Sending Prod listeners...")
        else:
            self.response = scistream_pb2.Response(
                listeners = entry["listeners"]
            )
            AppResponse = scistream_pb2.AppResponse(message="Sending listeners...")
        self.logger.info("Sending listeners to S2UC...")
        entry["hello_received"].set()
        return AppResponse

def start(listener_ip='127.0.0.1', port=5000, v=False, verbose=False):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    scistream_pb2_grpc.add_ControlServicer_to_server(S2CS(listener_ip, v or verbose), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Server started on {listener_ip}:{port}")
    server.wait_for_termination()

if __name__ == '__main__':
    try:
        fire.Fire(start)
    except KeyboardInterrupt:
        print("\nTerminating server")
        sys.exit(0)
