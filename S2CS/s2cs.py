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

            # TODO: Change logic to allow for more than one S2DS subprocess
            if (entry["role"] == "PROD"):
                assert ("s2ds_proc" in entry) and entry["s2ds_proc"] != None, "S2DS subprocess was not launched!"
                assert ("prod_listeners" in entry) and entry["prod_listeners"] != None, "Prod S2CS never received or did not correctly process ProdApp Hello"
                # TODO: Allow remote-host to be configurable
                remote_connection = "127.0.0.1" + ":" + entry["prod_listeners"] + "\n"
                # TODO: Check that process is still running
                entry["s2ds_proc"].stdin.write(remote_connection.encode())
                entry["s2ds_proc"].stdin.flush()
                print("S2DS subprocess establishing connection with %s..." % remote_connection.split("\n")[0])
            else:
                assert ("s2ds_proc" in entry) or entry["s2ds_proc"] != None, "S2DS subprocess was not launched!"
                # TODO: Allow remote-host to be configurable
                remote_connection = "127.0.0.1" + ":" + req["remote_port"] + "\n"
                # TODO: Check that process is still running
                entry["s2ds_proc"].stdin.write(remote_connection.encode())
                entry["s2ds_proc"].stdin.flush()
                print("S2DS subprocess establishing connection with %s..." % remote_connection.split("\n")[0])
            print("Targets updated")
            self.resp = pickle.dumps("Targets updated")
        # Releasing resources
        elif tag == "S2UC_REL":
            req = event.kwargs.get('req', None)
            removed_item = self.kvs.pop(req["uid"], None)
            assert removed_item != None, "S2CS could not find entry with key '%s'" % req["uid"]

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

        print("Reserving resources...")

        # TODO: Allow for multiple connections / more than one S2DS subprocess
        assert entry["num_conn"] == 1, "Only one connection is supported right now"
        assert ("s2ds_proc" not in entry) or entry["s2ds_proc"] == None, "S2DS subprocess already launched!"

        print("Starting S2DS subprocess...")
        # TODO: Combine repos for reliable relative path
        origWD = os.getcwd()
        os.chdir(os.path.join(os.path.abspath(sys.path[0]), '../../scistream/S2DS'))
        entry["s2ds_proc"] = subprocess.Popen(['./S2DS.out'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        os.chdir(origWD)
        # TODO: Make sure there are no errors in the returned port
        listener_port = entry["s2ds_proc"].stdout.readline().decode("utf-8").split("\n")[0]
        # TODO: Figure out where local ip address should come from
        entry["listeners"] = ["127.0.0.1" + ":" + listener_port]
        print("S2DS subprocess reserved listeners: %s" % entry["listeners"])

        print("Resources reserved")
        self.resp = pickle.dumps(entry["listeners"])

    def send_prod_lstn(self, event):
        req = event.kwargs.get('req', None)
        entry = self.kvs[req["uid"]]
        if entry["role"] == "PROD":
            self.svr_socket.send_string("Sending Prod listeners...")
            print("Binding Prod listeners...")
            # TODO: Need to check if ports are already open in buffer-and-forward element??
            # TODO: Send to s2uc.py and "bind" after connection map is created
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
            # TODO: Signal to producer/consumer that request was released?
            s2cs.RESP()
            print("Current state: %s " % s2cs.state)

        elif message['cmd'] == 'ERROR':
            # Testing User ERROR
            s2cs.ERROR()
            print("Current state: %s " % s2cs.state)
            s2cs.ErrorRel(resp="Clear KVS after errors...")

        else:
            s2cs.socket.send_string("RESP: %s message not supported" % message)
