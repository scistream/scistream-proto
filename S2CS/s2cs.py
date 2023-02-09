"""
    S2CS state machine implementation
"""

from transitions import Machine
from optparse import OptionParser
from itertools import cycle, islice
import random
import zmq
import pickle
import signal
import sys
import os
import subprocess
import json
import logging
import models

s2cs_logger = logging.getLogger("s2cs.py")

# Parse command line options and dump results
def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option('--s2-port', dest='s2_port', default="5000", help='S2UC->S2CS server port')
    parser.add_option('--app-port', dest='app_port', default="5500", help='ProdApp/ConsApp->S2CS server port')
    parser.add_option('--listener-ip', dest='listener_ip', default="127.0.0.1", help='Local IP address of listeners')
    parser.add_option("--v", action="store_true", dest="verbose", default=False, help="Verbose output")
    (options, args) = parser.parse_args()

    return options, args

def recv(socket):
    s2_request = socket.recv()
    s2_message = pickle.loads(s2_request)
    print("\nReceived S2UC request:", s2_message['cmd'])

    # Requesting resources
    if s2_message['cmd'] == 'REQ':
        s2cs.client_request(s2_message)
        s2cs.client_reserve(s2_message)

    # Updating targets
    elif s2_message['cmd'] == 'UpdateTargets':
        s2cs.client_update(s2_message)
        socket.send(s2cs.resp)
    # Releasing resources
    elif s2_message['cmd'] == 'REL':
        s2cs.release(s2_message)
        socket.send(s2cs.resp)
    elif s2_message['cmd'] == 'Hello':
        s2cs.send_prod_lstn(s2_message)
        s2cs.send_resp(None)
    # Error in request sent from S2UC
    elif s2_message['cmd'] == 'ERROR':
        s2cs.release(s2_message)
        socket.send(s2cs.resp)
    # Unknown command
    else:
        socket.send_string("S2CS ERROR: %s message not supported" % s2_message)

class S2CS():
    def client_request(self,request):
        print("Client Requesting Resources")
        #models.validate_request(models.ClientRequest, request)
        uid = request["uid"]
        self.kvs[uid] = {
                  "role": request['role'],
                  "num_conn": request['num_conn'],
                  "rate": request['rate']
        }
        s2cs_logger.info("Added key: '%s' with entry: %s" % (uid, self.kvs.get(uid)))

    def client_update(self,request):
        print("Updating targets...")
        #data model validation could be better here
        ## replace Value error for s2cs error
        #models.validate_request(model.ClientRequest, request)
        if request["uid"] not in self.kvs:
            raise ValueError("Attempting to update nonexistent entry with key '%s'" % request["uid"])
        entry = self.kvs[request["uid"]]
        #models.validate_entry(request,entry)
        if (entry["role"] == "PROD"):
            if len(request["remote_listeners"]) < entry["num_conn"]:
                request["remote_listeners"] = list(islice(cycle(req["remote_listeners"]), entry["num_conn"]))
        else:
            entry["prods2cs_listeners"] = request["remote_listeners"] # Include remote listeners for transparency to user

        # Send remote port information to S2DS subprocesses in format "remote_ip:remote_port\n"
        for i in range(len(request["remote_listeners"])):
            curr_proc = entry["s2ds_proc"][i]
            curr_remote_conn = request["remote_listeners"][i] + "\n"
            assert (curr_proc.poll() is None), "S2DS subprocess with PID '%d' unexpectedly quit" % curr_proc.pid
            curr_proc.stdin.write(curr_remote_conn.encode())
            curr_proc.stdin.flush()
            print("S2DS subprocess establishing connection with %s..." % curr_remote_conn.split("\n")[0])

        print("Targets updated")
        self.resp = pickle.dumps("Targets updated")

    def release(self, req):
        print("Releasing S2DS resources...")
        uid = req.get('uid', None)
        assert uid != None and uid != "", "Invalid uid '%s'" % uid
        # is this ever
        resp ="Resources released"
        self.release_request(uid)
        self.resp = pickle.dumps(resp)
        print("Released S2DS resources")

    # Reserve resources for incoming requests

    def client_reserve(self, req):
        uid = req.get('uid', None)
        assert uid != None and uid != "", "Invalid uid '%s'" % uid
        entry = self.kvs.get(uid, None)
        assert entry != None, "S2CS could not find entry with key '%s'" % uid
        print("Reserving resources...")

        assert entry["num_conn"] > 0, "Must have at least one connection"
        assert ("s2ds_proc" not in entry) or entry["s2ds_proc"] == [], "S2DS subprocess already launched!"
        assert ("listeners" not in entry) or entry["listeners"] == [], "S2DS subprocess already launched!"

        print("Starting S2DS subprocess(es)...")
        # TODO: Combine repos for reliable relative path
        origWD = os.getcwd()
        os.chdir(os.path.join(os.path.abspath(sys.path[0]), '../scistream/S2DS'))
        entry["s2ds_proc"] = []
        entry["listeners"] = []

        for _ in range(entry["num_conn"]):
            new_proc = subprocess.Popen(['./S2DS.out'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            new_listener_port = new_proc.stdout.readline().decode("utf-8").split("\n")[0] # Read listener port from S2DS subprocess
            assert (int(new_listener_port) > 0 and int(new_listener_port) <= 65535), "S2DS subprocess returned invalid listener port '%s'" % new_listener_port
            new_listener = self.listener_ip + ":" + new_listener_port
            entry["s2ds_proc"].append(new_proc)
            entry["listeners"].append(new_listener)

        os.chdir(origWD)

        s2cs_logger.info("S2DS subprocess(es) reserved listeners: %s" % entry["listeners"])
        print("Resources reserved")
        self.resp = pickle.dumps(entry["listeners"])

    # Release all resources in use by S2CS
    def release_all_resources(self):
        print("Releasing all resources...")
        for uid in list(self.kvs):
            self.release_request(uid)
        print("Released all resources")

    # Release all resources used by a particular request
    def release_request(self, uid):
        removed_item = self.kvs.pop(uid, None)

        assert removed_item != None, "S2CS could not find entry with key '%s'" % uid

        if ("s2ds_proc" in removed_item and removed_item["s2ds_proc"] != []):
            for i, rem_proc in enumerate(removed_item["s2ds_proc"]):
                rem_proc.terminate() # TODO: Make sure s2ds buffer handles this signal gracefully
                removed_item["s2ds_proc"][i] = rem_proc.pid # Print out PID rather than Popen object
            s2cs_logger.info("Terminated %d S2DS subprocess(es)" % len(removed_item["s2ds_proc"]))

        s2cs_logger.info("Removed key: '%s' with entry: %s" % (uid, removed_item))


    # Create entry of connection information to send to S2UC
    def send_prod_lstn(self, req):
        uid = req.get('uid', None)
        assert uid != None and uid != "", "Invalid uid '%s'" % uid
        entry = self.kvs.get(uid, None)
        assert entry != None, "S2CS could not find entry with key '%s'" % uid

        if entry["role"] == "PROD":
            self.app_svr_socket.send(pickle.dumps("Sending Prod listeners..."))
            entry["prod_listeners"] = req["prod_listeners"]
            s2cs_logger.info("Received Prod listeners: %s" % entry["prod_listeners"])
            entry = {
                      "listeners": entry["listeners"],
                      "prod_listeners": entry["prod_listeners"]
            }
        else:
            entry = {
                      "listeners": entry["listeners"]
            }
            self.app_svr_socket.send(pickle.dumps(entry)) # Send consumer s2ds listeners to ConsApp

        # TODO: Only send producer s2ds "listeners" to S2UC?
        print("Sending listeners to S2UC...")
        self.resp = pickle.dumps(entry)


    # Send value in "self.resp" to S2UC
    def send_resp(self, event):
        #resp = event.kwargs.get('resp', None)
        self.s2_svr_socket.send(self.resp)
    # Error handler
    def handle_error(self, event):
        err_msg = "ERROR: S2CS %s" % event.error
        print(err_msg)

        # Send error responses to ProdApp/ConsApp
        if (event.event.name == "Hello"):
            self.app_svr_socket.send_string(err_msg)
            self.resp = pickle.dumps(err_msg)
            raise AssertionError(err_msg)

        # Send error responses to S2UC
        if (event.event.name == "REL" or event.event.name == "ErrorRel"):
            self.resp = pickle.dumps(err_msg)
            self.send_resp(event)
            raise AssertionError(err_msg)

        s2cs.release(s2_message)
        self.send_resp(event)
        raise AssertionError(err_msg)

    def start(self):
        while True:
            try:
                sockets  = dict(self.poller.poll())
                a= [ recv(s) for s in sockets]
            except ValueError as e:
                print(e)
            except AssertionError:
                #validation error
                print("ERROR: S2CS encountered AssertionError")
            except KeyboardInterrupt:
                self.release_all_resources()
                break
            except Exception as e:
                print(e)
                print("ERROR: S2CS Unexpected error", sys.exc_info()[0])
                self.release_all_resources()
                break

    def create_socket(self, socket_type, port):
        context = zmq.Context()
        socket = context.socket(socket_type)
        socket.bind("tcp://*:%s" % port)
        self.poller.register(socket, zmq.POLLIN)
        return socket

    # Initialize S2CS object
    def __init__(self, s2_port, app_port, listener_ip):
        self.kvs = {}
        self.resp = None
        self.listener_ip = listener_ip

        self.poller = zmq.Poller()
        self.s2_svr_socket = self.create_socket(zmq.REP, s2_port)
        print("S2UC->S2CS server running on port TCP/%s" % s2_port)

        self.app_svr_socket = self.create_socket(zmq.REP, app_port)
        print("ProdApp/ConsApp->S2CS server running on port TCP/%s" % app_port)

if __name__ == '__main__':
    opts, args = parseOptions()

    # Verbose logging output
    if opts.verbose:
        formatter = logging.Formatter(fmt="%(message)s")
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        s2cs_logger.addHandler(handler)
        s2cs_logger.setLevel(logging.INFO)
    s2cs = S2CS(opts.s2_port, opts.app_port, opts.listener_ip)
    s2cs.start()
