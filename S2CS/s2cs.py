"""
    S2CS state machine implementation
"""

from itertools import cycle, islice
from models import S2CSException
import zmq
import pickle
import sys
import os
import subprocess
import logging
import models
import fire

class S2CS():

    def start(self):
        while True:
            try:
                sockets  = dict(self.poller.poll())
                a= [ self.recv(s) for s in sockets]
            #TODO error handling
            except models.S2CSException as e:
                self.logger.warning(str(e))
            except KeyboardInterrupt:
                self.release_all_resources()
                break
            except Exception as e:
                self.logger.debug(e)
                self.logger.warning("ERROR: S2CS Unexpected error", sys.exc_info()[0])
                self.release_all_resources()
                break

    def create_socket(self, socket_type, port):
        context = zmq.Context()
        socket = context.socket(socket_type)
        socket.bind("tcp://*:%s" % port)
        self.poller.register(socket, zmq.POLLIN)
        return socket

    def __init__(self, s2_port, app_port, listener_ip, v=False, verbose=False):
        self.kvs = {}
        self.resp = None
        self.listener_ip = listener_ip

        self.logger = logging.getLogger(__name__)
        formatter = logging.Formatter(fmt="%(message)s")
        handler = logging.StreamHandler(sys.stdout)
        self.logger.setLevel(logging.DEBUG)
        if v or verbose:
            handler.setLevel(logging.DEBUG)
        else:
            handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.poller = zmq.Poller()
        self.s2_svr_socket = self.create_socket(zmq.REP, s2_port)
        self.logger.info("S2UC->S2CS server running on port TCP/%s" % s2_port)

        self.app_svr_socket = self.create_socket(zmq.REP, app_port)
        self.logger.info("ProdApp/ConsApp->S2CS server running on port TCP/%s" % app_port)

        #self.start()

    def recv(self, socket):
        ## WHAT IF THERE IS AN EXCEPTION HERE?
        s2_request = socket.recv()
        s2_message = pickle.loads(s2_request)
        self.logger.info("\nReceived S2UC request: %s" % s2_message['cmd'])
        # Requesting resources
        if s2_message['cmd'] == 'REQ':
            self.client_request(s2_message)
            ### TODO Add a Timeout to this
        # Updating targets
        elif s2_message['cmd'] == 'Hello':
            self.send_prod_lstn(s2_message)
            self.s2_svr_socket.send(self.resp)
            # Error in request sent from S2UC
        elif s2_message['cmd'] == 'UpdateTargets':
            self.client_update(s2_message)
            socket.send(self.resp)
        # Releasing resources
        elif s2_message['cmd'] == 'REL':
            self.release(s2_message)
            socket.send(self.resp)
        elif s2_message['cmd'] == 'ERROR':
            self.release(s2_message)
            socket.send(self.resp)
        else:
            socket.send_string("S2CS ERROR: %s message not supported" % s2_message)

    def client_request(self,request):
        # What are the failure scenarios for this function
        self.logger.info("Client Requesting Resources")
        models.validate_request(request)
        uid = request["uid"]
        if uid in self.kvs:
            raise S2CSException("entry already found for uid")
        self.kvs[uid] = {
                  "role": request['role'],
                  "num_conn": request['num_conn'],
                  "rate": request['rate']
        }
        self.logger.debug("Added key: '%s' with entry: %s" % (uid, self.kvs[uid]))
        entry = self.startS2DS(self.kvs[uid])
        self.logger.debug("S2DS subprocess(es) reserved listeners: %s" % entry["listeners"])
        self.logger.info("Resources reserved")
        self.resp = pickle.dumps(self.kvs[uid]["listeners"])
        ## WAITS FOR MESSAGE ON APP SOCKET

    def client_update(self,request):
        self.logger.info("Updating targets...")
        if request["uid"] not in self.kvs:
            raise S2CSException("Attempting to update nonexistent entry with key '%s'" % request["uid"])
        entry = self.kvs[request["uid"]]
        models.validate_update(request,entry)
        if (entry["role"] == "PROD"):
            if len(request["remote_listeners"]) < entry["num_conn"]:
                request["remote_listeners"] = list(islice(cycle(request["remote_listeners"]), entry["num_conn"]))
        else:
            entry["prods2cs_listeners"] = request["remote_listeners"] # Include remote listeners for transparency to user
        # Send remote port information to S2DS subprocesses in format "remote_ip:remote_port\n"
        for i in range(len(request["remote_listeners"])):
            curr_proc = entry["s2ds_proc"][i]
            curr_remote_conn = request["remote_listeners"][i] + "\n"
            if curr_proc.poll() is not None:
                raise S2CSException("S2DS subprocess with PID '%d' unexpectedly quit" % curr_proc.pid)
            curr_proc.stdin.write(curr_remote_conn.encode())
            curr_proc.stdin.flush()
            self.logger.info("S2DS subprocess establishing connection with %s..." % curr_remote_conn.split("\n")[0])
        self.logger.info("Targets updated")
        self.resp = pickle.dumps("Targets updated")

    def release(self, req):
        self.logger.debug("Releasing S2DS resources...")
        models.validate_uid(req)
        self.release_request(req["uid"])
        self.resp = pickle.dumps("Resources released")
        self.logger.info("Released S2DS resources")

    def startS2DS(self, entry):
        """
        TODO this can be improved
        """
        self.logger.info("Starting S2DS subprocess(es)...")
        #S2DS_script = pathlib.Path.cwd()/'scistream/S2'
        origWD = os.getcwd()
        os.chdir(os.path.join(os.path.abspath(sys.path[0]), '../scistream/S2DS'))
        entry["s2ds_proc"] = []
        entry["listeners"] = []
        for _ in range(entry["num_conn"]):
            new_proc = subprocess.Popen(['./S2DS.out'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            new_listener_port = new_proc.stdout.readline().decode("utf-8").split("\n")[0] # Read listener port from S2DS subprocess
            if int(new_listener_port) < 0 or int(new_listener_port) > 65535:
                raise S2CSException("S2DS subprocess returned invalid listener port '%s'" % new_listener_port)
            new_listener = self.listener_ip + ":" + new_listener_port
            entry["s2ds_proc"].append(new_proc)
            entry["listeners"].append(new_listener)
        os.chdir(origWD)
        return entry

    # Release all resources in use by S2CS
    def release_all_resources(self):
        self.logger.info("Releasing all resources...")
        for uid in list(self.kvs):
            self.release_request(uid)
        self.logger.info("Released all resources")

    # Release all resources used by a particular request
    def release_request(self, uid):
        if uid not in self.kvs:
            raise S2CSException("Attempting to release unexistent uid")
        removed_item = self.kvs.pop(uid, None)
        if ("s2ds_proc" in removed_item and removed_item["s2ds_proc"] != []):
            for i, rem_proc in enumerate(removed_item["s2ds_proc"]):
                rem_proc.terminate() # TODO: Make sure s2ds buffer handles this signal gracefully
                removed_item["s2ds_proc"][i] = rem_proc.pid # Print out PID rather than Popen object
            self.logger.info("Terminated %d S2DS subprocess(es)" % len(removed_item["s2ds_proc"]))

        self.logger.debug("Removed key: '%s' with entry: %s" % (uid, removed_item))

    # Create entry of connection information to send to S2UC
    def send_prod_lstn(self, req):
        #What are the failure scenarios here
        models.validate_uid(req)
        uid=req["uid"]
        if uid not in self.kvs:
            raise S2CSException("Attempting to update unexistent uid")
        entry = self.kvs[uid]
        if entry["role"] == "PROD":
            self.app_svr_socket.send(pickle.dumps("Sending Prod listeners..."))
            entry["prod_listeners"] = req["prod_listeners"]
            self.logger.debug("Received Prod listeners: %s" % entry["prod_listeners"])
            response = {
                      "listeners": entry["listeners"],
                      "prod_listeners": entry["prod_listeners"]
            }
        else:
            response = {
                      "listeners": entry["listeners"]
            }
            self.app_svr_socket.send(pickle.dumps(response)) # Send consumer s2ds listeners to ConsApp

        # TODO: Only send producer s2ds "listeners" to S2UC?
        self.logger.info("Sending listeners to S2UC...")
        self.resp = pickle.dumps(response)

if __name__ == '__main__':
    fire.Fire(S2CS)
