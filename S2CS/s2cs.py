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
    parser.add_option('--s2-port', dest='s2_port', default="5000", help='S2UC->S2CS server port')
    parser.add_option('--app-port', dest='app_port', default="5500", help='ProdApp/ConsApp->S2CS server port')
    (options, args) = parser.parse_args()

    return options, args

class S2CS(Machine):
    # Update key-value pairs in dictionary for request entries
    def update_kvs(self, event):
        tag = event.kwargs.get('tag', None)

        ### Requesting resources
        if tag == "S2UC_REQ":
            req = event.kwargs.get('req', None)
            entry = {
                      "role": req['role'],
                      "num_conn": req['num_conn'],
                      "rate": req['rate']
            }
            self.kvs[req["uid"]] = entry
            print("Added key: '%s' with entry: %s" % (req["uid"], self.kvs))

        ### Updating targets
        elif tag == "S2UC_UPD":
            print("Updating targets...")
            req = event.kwargs.get('req', None)
            entry = self.kvs[req["uid"]]

            assert ("s2ds_proc" in entry) and entry["s2ds_proc"] != None, "S2DS subprocess was not launched!"
            assert req["local_listeners"] == entry["listeners"][0], "S2UC connection map does not match S2CS listeners"

            # TODO: Change logic to allow for more than one S2DS subprocess
            if (entry["role"] == "PROD"):
                assert ("prod_listeners" in entry) and entry["prod_listeners"] != None, "Prod S2CS never received or did not correctly process ProdApp Hello"
                assert req["remote_listeners"] == entry["prod_listeners"], "S2UC connection map does not match Prod S2CS ProdApp listeners"
                remote_connection = entry["prod_listeners"] + "\n"
            else:
                remote_connection = req["remote_listeners"] + "\n"
                entry["prods2cs_listeners"] = req["remote_listeners"] # Include remote listeners for transparency to user

            # TODO: Check that process is still running
            entry["s2ds_proc"].stdin.write(remote_connection.encode())
            entry["s2ds_proc"].stdin.flush()
            print("S2DS subprocess establishing connection with %s..." % remote_connection.split("\n")[0])
            print("Targets updated")
            self.resp = pickle.dumps("Targets updated")

        ### Releasing resources
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

        ### Unknown message
        else:
            print("Unrecognized message")

    # Reserve resources for incoming requests
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

    # Create entry of connection information to send to S2UC
    def send_prod_lstn(self, event):
        req = event.kwargs.get('req', None)
        entry = self.kvs[req["uid"]]

        if entry["role"] == "PROD":
            self.app_svr_socket.send_string("Sending Prod listeners...")
            entry["prod_listeners"] = req["prod_listeners"]
            print("Received Prod listeners: %s" % entry["prod_listeners"])
            entry = {
                      "listeners": entry["listeners"],
                      "prod_listeners": entry["prod_listeners"]
            }
        else:
            self.app_svr_socket.send_string("I'm Cons, nothing to send.")
            entry = {
                      "listeners": entry["listeners"],
            }
        self.resp = pickle.dumps(entry)

    # Send value in "self.resp" to S2UC
    def send_resp(self, event):
        #resp = event.kwargs.get('resp', None)
        if self.resp != "":
            self.s2_svr_socket.send(self.resp)

    # Initialize S2CS object
    def __init__(self, s2_port, app_port):
        self.kvs = {}
        self.resp = None

        # Create S2UC->S2CS server side
        s2_svr_context = zmq.Context()
        self.s2_svr_socket = s2_svr_context.socket(zmq.REP)
        self.s2_svr_socket.bind("tcp://*:%s" % s2_port)
        print("S2UC->S2CS server running on port TCP/%s" % s2_port)

        # Creare ProdApp/ConsApp->S2CS server side
        app_svr_context = zmq.Context()
        self.app_svr_socket = app_svr_context.socket(zmq.REP)
        self.app_svr_socket.bind("tcp://*:%s" % app_port)
        print("ProdApp/ConsApp->S2CS server running on port TCP/%s" % app_port)

        states = ['idle', 'reserving', 'listening', 'updating', 'releasing']

        transitions = [
            { 'trigger': 'REQ', 'source': 'idle', 'dest': 'reserving', 'before': 'update_kvs'},
            { 'trigger': 'Reserve', 'source': 'reserving', 'dest': 'listening', 'before': 'reserve_resources'},
            { 'trigger': 'Hello', 'source': 'listening', 'dest': 'idle', 'before': 'send_prod_lstn', 'after': 'send_resp'},
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
    s2cs = S2CS(opts.s2_port, opts.app_port)

    while True:
        #  Wait for next request from S2UC or Prod/Cons App
        s2_request = s2cs.s2_svr_socket.recv()
        s2_message = pickle.loads(s2_request)
        print("Received S2UC request:", s2_message['cmd'])

        if s2_message['cmd'] == 'REQ':
            s2cs.REQ(req=s2_message, tag="S2UC_REQ", info="Requesting resources...")
            print("Current state: %s " % s2cs.state)
            s2cs.Reserve(req=s2_message)
            print("Current state: %s " % s2cs.state)

            # Listen on ProdApp/ConsApp port for Hello
            app_request = s2cs.app_svr_socket.recv()
            app_message = pickle.loads(app_request)
            print("Received App request:", app_message['cmd'])

            if app_message['cmd'] == 'Hello':
                s2cs.Hello(req=app_message)
                print("Current state: %s " % s2cs.state)
            else:
                s2cs.app_svr_socket.send_string("RESP: %s message not supported" % app_message)

        elif s2_message['cmd'] == 'UpdateTargets':
            # Testing UpdateTargets
            s2cs.UpdateTargets(req=s2_message, tag="S2UC_UPD")
            print("Current state: %s " % s2cs.state)
            s2cs.RESP()
            print("Current state: %s " % s2cs.state)

        elif s2_message['cmd'] == 'REL':
            # Testing User REL
            s2cs.REL(req=s2_message, tag="S2UC_REL", info="Releasing resources...")
            print("Current state: %s " % s2cs.state)
            # TODO: Signal to producer/consumer that request was released?
            s2cs.RESP()
            print("Current state: %s " % s2cs.state)

        elif s2_message['cmd'] == 'ERROR':
            # Testing User ERROR
            s2cs.ERROR()
            print("Current state: %s " % s2cs.state)
            s2cs.ErrorRel(resp="Clear KVS after errors...")

        else:
            s2cs.s2_svr_socket.send_string("RESP: %s message not supported" % s2_message)
