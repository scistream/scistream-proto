"""
    S2CS state machine implementation
"""

from transitions import Machine
from time import sleep
from optparse import OptionParser
import random
import zmq
import pickle
import signal
import sys
import os
import subprocess
import json

# Parse command line options and dump results
def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option('--port', dest='port', default="5000", help='S2CS server port')
    (options, args) = parser.parse_args()

    return options, args

class S2CS(Machine):
    def update_kvs(self, event):
        tag = event.kwargs.get('tag', None)

        # Requesting resources
        if tag == "S2UC_REQ":
            req = event.kwargs.get('req', None)
            entry = {
                      "role": req['role'],
                      "num_conn": req['num_conn'],
                      "rate": req['rate']
            }
            self.kvs[req["uid"]] = entry
            print("Added key: '%s' with entry: %s" % (req["uid"], self.kvs))
        # Received response
        elif tag == "S2UC_RESP":
            pass
        # Updating targets
        elif tag == "S2UC_UPD":
            print("Updating targets...")
            req = event.kwargs.get('req', None)
            entry = self.kvs[req["uid"]]

            # TODO: Combine repos for reliable relative path
            # TODO: Change logic to allow for more than one S2DS subprocess
            # TODO: Spawn s2ds process when first reserving resources and remove most logic below
            if (entry["role"] == "PROD"):
                assert ("s2ds_proc" not in entry) or entry["s2ds_proc"] == None, "S2DS subprocess already launched!"
                assert ("prod_listeners" in entry) and entry["prod_listeners"] != None, "Prod S2CS never received or did not correctly process ProdApp Hello"
                origWD = os.getcwd()
                os.chdir(os.path.join(os.path.abspath(sys.path[0]), '../../scistream/S2DS'))
                entry["s2ds_proc"] = subprocess.Popen(['./S2DS.out', '--remote-port', entry["prod_listeners"], '--local-port', str(req["local_port"]), '--remote-host', '127.0.0.1'])
                os.chdir(origWD)
                print("Starting S2DS subprocess with local-port %s and remote-port %s..." % (req["local_port"], entry["prod_listeners"]))
            else:
                assert ("s2ds_proc" not in entry) or entry["s2ds_proc"] == None, "S2DS subprocess already launched!"
                origWD = os.getcwd()
                os.chdir(os.path.join(os.path.abspath(sys.path[0]), '../../scistream/S2DS'))
                entry["s2ds_proc"] = subprocess.Popen(['./S2DS.out', '--remote-port', str(req["remote_port"]), '--local-port', str(req["local_port"]), '--remote-host', '127.0.0.1'])
                os.chdir(origWD)
                print("Starting S2DS subprocess with local-port %s and remote-port %s..." % (req["local_port"], req["remote_port"]))
            print("Targets updated")
            self.resp = pickle.dumps("Targets updated")
        elif tag == "S2UC_REL":
            req = event.kwargs.get('req', None)
            removed_item = self.kvs.pop(req["uid"], None)
            assert removed_item != None, "S2CS could not find entry with key '%s'" % req["uid"]
            # FREE
            print("Releasing S2DS resources...")
            if ("s2ds_proc" in removed_item and removed_item["s2ds_proc"] != None):
                removed_item["s2ds_proc"].terminate()
                removed_item["s2ds_proc"] = removed_item["s2ds_proc"].pid # Print out PID rather than Popen object
                print("Terminated S2DS subprocess")

            self.resp = pickle.dumps("Resources released")
            print("Removed key: '%s' with entry: %s" % (req["uid"], removed_item))
        else:
            print("Unrecognized message")

    def reserve_resources(self, event):
        req = event.kwargs.get('req', None)
        entry = self.kvs[req["uid"]]

        listeners = []
        # TODO: Update buffer-and-forward elements to select free port
        print("Reserving resources...")

        if entry["role"] == "PROD":
            pool = "5000"
        else:
            pool = "4000"

        if entry["num_conn"] > 1:
            for i in range(entry["num_conn"]):
                listeners.append("localhost:%s%s" % (pool, i))
        else:
            listeners.append("localhost:%s0" % pool)

        print("Reserved listeners:", listeners)
        entry["listeners"] = listeners
        self.resp = pickle.dumps(listeners)

    def send_prod_lstn(self, event):
        req = event.kwargs.get('req', None)
        entry = self.kvs[req["uid"]]
        if entry["role"] == "PROD":
            self.svr_socket.send_string("Sending Prod listeners...")
            print("Binding Prod listeners...")
            # TODO: Check if ports are open in buffer-and-forward element
            # TODO: Send to buffer-and-forward element to bind
            entry["prod_listeners"] = req["prod_listeners"]
            print("Binded Prod listeners: %s" % entry["prod_listeners"])

        else:
            self.svr_socket.send_string("I'm Cons, nothing to send.")

    def send_resp(self, event):
        #resp = event.kwargs.get('resp', None)
        self.svr_socket.send(self.resp)

    def __init__(self, port):
        self.kvs = {}
        self.resp = None

        # Create S2CS server side
        svr_context = zmq.Context()
        self.svr_socket = svr_context.socket(zmq.REP)
        self.svr_socket.bind("tcp://*:%s" % port)
        print("S2CS server running on port TCP/%s" % port)

        states = ['idle', 'reserving', 'listening', 'updating', 'releasing']

        transitions = [
            { 'trigger': 'REQ', 'source': 'idle', 'dest': 'reserving', 'before': 'update_kvs'},
            { 'trigger': 'Reserve', 'source': 'reserving', 'dest': 'listening', 'before': 'reserve_resources', 'after': 'send_resp'},
            # { 'trigger': 'RESP', 'source': 'reserving', 'dest': 'listening', 'before': 'update_kvs', 'after': 'send_resp'},
            { 'trigger': 'Hello', 'source': 'listening', 'dest': 'idle', 'before': 'send_prod_lstn'},
            { 'trigger': 'REL', 'source': 'idle', 'dest': 'releasing', 'before': 'update_kvs'},
            { 'trigger': 'RESP', 'source': 'releasing', 'dest': 'idle', 'after': 'send_resp'},
            { 'trigger': 'UpdateTargets', 'source': 'idle', 'dest': 'updating', 'before': 'update_kvs'},
            { 'trigger': 'RESP', 'source': 'updating', 'dest': 'idle', 'after': 'send_resp'},
            { 'trigger': 'ERROR', 'source': ['reserving', 'listening', 'updating'], 'dest': 'releasing'},
            { 'trigger': 'ErrorRel', 'source': 'releasing', 'dest': 'idle', 'before': 'update_kvs', 'after': 'send_resp'},
        ]

        Machine.__init__(self, states=states, transitions=transitions, send_event=True, initial='idle')

if __name__ == '__main__':
    opts, args = parseOptions()
    s2cs = S2CS(opts.port)

    while True:
        #  Wait for next request from S2UC or Prod/Cons App
        request = s2cs.svr_socket.recv()
        message = pickle.loads(request)
        print("Received request:", message['cmd'])

        if message['cmd'] == 'REQ':
            s2cs.REQ(req=message, tag="S2UC_REQ", info="Requesting resources...")
            print("Current state: %s " % s2cs.state)
            s2cs.Reserve(req=message)
            print("Current state: %s " % s2cs.state)
            # s2cs.RESP(tag="S2UC_RESP")
            # print("Current state: %s " % s2cs.state)

        elif message['cmd'] == 'Hello':
            s2cs.Hello(req=message)
            print("Current state: %s " % s2cs.state)
            # TODO: Send response to S2UC containing all information?

        elif message['cmd'] == 'UpdateTargets':
            # Testing UpdateTargets
            s2cs.UpdateTargets(req=message, tag="S2UC_UPD")
            print("Current state: %s " % s2cs.state)
            s2cs.RESP()
            print("Current state: %s " % s2cs.state)

        elif message['cmd'] == 'REL':
            # Testing User REL
            s2cs.REL(req=message, tag="S2UC_REL", info="Releasing resources...")
            print("Current state: %s " % s2cs.state)
            s2cs.RESP()
            print("Current state: %s " % s2cs.state)

        elif message['cmd'] == 'ERROR':
            # Testing User ERROR
            s2cs.ERROR()
            print("Current state: %s " % s2cs.state)
            s2cs.ErrorRel(resp="Clear KVS after errors...")

        else:
            s2cs.socket.send_string("RESP: %s message not supported" % message)
