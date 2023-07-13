import sys
import fire
import grpc
import threading

from proto import scistream_pb2
from proto import scistream_pb2_grpc

from concurrent import futures
from s2ds import S2DS
#, Haproxy, Nginx
from utils import request_decorator, set_verbosity, authenticated
import utils
from globus_sdk import ConfidentialAppAuthClient

class S2CSException(Exception):
    pass

def get_auth_client():
    """Create a Globus Auth client from config info"""
    client = ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)
    return client

class S2CS(scistream_pb2_grpc.ControlServicer):
    TIMEOUT = 180 #timeout value in seconds
    def __init__(self, listener_ip, verbose):
        self.response = None
        self.resource_map = {}
        self.listener_ip = listener_ip
        set_verbosity(self, verbose)

    #@validate_args(has=["role", "uid", "num_conn", "rate"])
    @request_decorator
    @authenticated
    def req(self, request: scistream_pb2.Request, context):
        self.resource_map[request.uid] = {
            "role": request.role,
            "num_conn": request.num_conn,
            "rate": request.rate,
            "hello_received": threading.Event(),
            "prod_listeners": []
        }
        self.logger.debug(f"Added key: '{request.uid}' with entry: {self.resource_map[request.uid]}")
        self.s2ds= S2DS()
        reply = self.s2ds.start(request.num_conn, self.listener_ip)
        self.resource_map[request.uid].update(reply)

        hello_received = self.resource_map[request.uid]['hello_received'].wait(S2CS.TIMEOUT)

        if not hello_received:
            self.release_request(request.uid)
            raise S2CSException(f"Hello not received within the timeout period")

        return self.response

    @request_decorator
    @authenticated
    def update(self, request, context):
        #improve validation
        listeners=request.remote_listeners
        entry = self.resource_map[request.uid]
        if (request.role == "PROD"):
            listeners = [ listeners[ i % len(listeners) ] for i in range(entry["num_conn"]) ]
        else:
            entry["prods2cs_listeners"] = listeners
            # Include remote listeners for transparency to user
        self.s2ds.update_listeners(listeners, entry["s2ds_proc"])
        response = scistream_pb2.Response(listeners=entry["listeners"], prod_listeners=listeners)
        return response

    @request_decorator
    @authenticated
    def release(self, request, context):
        self.release_request(request.uid)
        response = scistream_pb2.Response()
        return response

    # Release all resources used by a particular request
    def release_request(self, uid):
        removed_item = self.resource_map.pop(uid, None)
        self.s2ds.release(removed_item)
        self.logger.debug(f"Removed key: '{uid}' with entry: {removed_item}")

    def release_all(self):
        uids = [i for i in self.resource_map]
        for i in uids:
            self.release_request(i)

    @request_decorator
    @authenticated
    def hello(self, request,context):
        ## Possible race condition here between REQ and HELLO
        entry = self.resource_map[request.uid]
        if request.role == "PROD":
            entry["prod_listeners"] = request.prod_listeners
            self.response = scistream_pb2.Response(listeners = entry["listeners"], prod_listeners = entry["prod_listeners"])
            AppResponse = scistream_pb2.AppResponse(message="Sending Prod listeners...")
        else:
            self.response = scistream_pb2.Response(listeners = entry["listeners"])
            AppResponse = scistream_pb2.AppResponse(message="Sending listeners...",
                listeners = entry["listeners"])
        entry["hello_received"].set()
        return AppResponse

    def validate_creds(self, token):
        client = get_auth_client()
        token_meta = client.oauth2_token_introspect(token)
        ## Scopes should be tied to deployment scopes

        print(token_meta)
        if not token_meta.get('active'):
            return False
            #raise ForbiddenError()
        return True

def start(listener_ip='0.0.0.0', port=5000, v=False, verbose=False):
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        servicer = S2CS(listener_ip, verbose=(v or verbose))
        scistream_pb2_grpc.add_ControlServicer_to_server(servicer, server)
        server.add_insecure_port(f'[::]:{port}')
        server.start()
        print(f"Server started on {listener_ip}:{port}")
        server.wait_for_termination()
    except KeyboardInterrupt:
        servicer.release_all()
        print("\nTerminating server")
        sys.exit(0)


if __name__ == '__main__':
        fire.Fire(start)
