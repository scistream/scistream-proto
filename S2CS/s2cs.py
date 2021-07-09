"""
    S2CS state machine implementation
"""

from transitions import Machine
from time import sleep
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
            print("Requesting resources...")
            req = event.kwargs.get('req', None)
            entry = {
                      "role": req['role'],
                      "num_conn": req['num_conn'],
                      "rate": req['rate']
            }
            self.kvs[req["uid"]] = entry
            print("Added key: '%s' with entry: %s" % (req["uid"], self.kvs.get(req["uid"])))

        ### Updating targets
        elif tag == "S2UC_UPD":
            print("Updating targets...")
            req = event.kwargs.get('req', None)
            entry = self.kvs[req["uid"]]

            assert ("s2ds_proc" in entry) and len(entry["s2ds_proc"]) == entry["num_conn"], "S2DS subprocess(es) not launched correctly!"
            assert req["local_listeners"] == entry["listeners"], "S2UC connection map does not match S2CS listeners"

            if (entry["role"] == "PROD"):
                assert ("prod_listeners" in entry) and entry["prod_listeners"] != None, "Prod S2CS never received or did not correctly process ProdApp Hello"
                assert req["remote_listeners"] == entry["prod_listeners"], "S2UC connection map does not match Prod S2CS ProdApp listeners"
                # TODO: Allow S2UC to handle mismatched number of listeners
                assert len(req["remote_listeners"]) <= entry["num_conn"], "ProdApp cannot have more listeners than Prod S2CS"
                if len(req["remote_listeners"]) < entry["num_conn"]:
                    req["remote_listeners"] = list(islice(cycle(req["remote_listeners"]), entry["num_conn"]))
            else:
                # TODO: Allow S2UC to handle mismatched number of listeners
                assert(len(req["remote_listeners"]) == entry["num_conn"]), "Prod/Cons S2CS must have same number of listeners"
                entry["prods2cs_listeners"] = req["remote_listeners"] # Include remote listeners for transparency to user

            # Send remote port information to S2DS subprocesses
            for i in range(len(req["remote_listeners"])):
                curr_proc = entry["s2ds_proc"][i]
                curr_remote_conn = req["remote_listeners"][i] + "\n"
                # TODO: Check that process is still running
                curr_proc.stdin.write(curr_remote_conn.encode())
                curr_proc.stdin.flush()
                print("S2DS subprocess establishing connection with %s..." % curr_remote_conn.split("\n")[0])

            print("Targets updated")
            self.resp = pickle.dumps("Targets updated")

        ### Releasing resources
        elif tag == "S2UC_REL" or tag == "S2UC_ERR":
            print("Releasing S2DS resources...")
            req = event.kwargs.get('req', None)
            resp = event.kwargs.get('resp', "Resources released")
            self.release_request(req["uid"])
            self.resp = pickle.dumps(resp)

        ### Unknown message
        else:
            self.resp = pickle.dumps("ERROR: Unrecognized message")
            print("ERROR: Unrecognized message")

    # Reserve resources for incoming requests
    def reserve_resources(self, event):
        req = event.kwargs.get('req', None)
        entry = self.kvs[req["uid"]]
        print("Reserving resources...")

        assert entry["num_conn"] > 0, "Must have at least one connection"
        assert ("s2ds_proc" not in entry) or entry["s2ds_proc"] == [], "S2DS subprocess already launched!"
        assert ("listeners" not in entry) or entry["listeners"] == [], "S2DS subprocess already launched!"

        print("Starting S2DS subprocess(es)...")
        # TODO: Combine repos for reliable relative path
        origWD = os.getcwd()
        os.chdir(os.path.join(os.path.abspath(sys.path[0]), '../../scistream/S2DS'))
        entry["s2ds_proc"] = []
        entry["listeners"] = []

        for _ in range(entry["num_conn"]):
            new_proc = subprocess.Popen(['./S2DS.out'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            # TODO: Make sure there are no errors in the returned port
            new_listener_port = new_proc.stdout.readline().decode("utf-8").split("\n")[0]
            # TODO: Figure out where local ip address should come from
            new_listener = "127.0.0.1" + ":" + new_listener_port

            entry["s2ds_proc"].append(new_proc)
            entry["listeners"].append(new_listener)

        os.chdir(origWD)

        print("S2DS subprocess(es) reserved listeners: %s" % entry["listeners"])
        print("Resources reserved")
        self.resp = pickle.dumps(entry["listeners"])

    # Release all resources in use by S2CS
    def release_all_resources(self, event):
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
            print("Terminated %d S2DS subprocess(es)" % len(removed_item["s2ds_proc"]))

        print("Removed key: '%s' with entry: %s" % (uid, removed_item))

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
                      "listeners": entry["listeners"]
            }
        self.resp = pickle.dumps(entry)

    # Send value in "self.resp" to S2UC
    def send_resp(self, event):
        #resp = event.kwargs.get('resp', None)
        self.s2_svr_socket.send(self.resp)

    # Error handler
    def handle_error(self, event):
        err_msg = "ERROR: %s" % event.error
        print(err_msg)

        if (event.event.name == "REL" or event.event.name == "ErrorRel"):
            self.resp = pickle.dumps(err_msg)
            self.send_resp(event)
            self.Reset()
            raise AssertionError(err_msg)

        self.ERROR()
        self.ErrorRel(req=event.kwargs.get('req', None), tag="S2UC_ERR", resp=err_msg)
        raise AssertionError(err_msg)

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
            { 'trigger': 'ERROR', 'source': '*', 'dest': 'releasing'},
            { 'trigger': 'ErrorRel', 'source': 'releasing', 'dest': 'idle', 'before': 'update_kvs', 'after': 'send_resp'},
            { 'trigger': 'Reset', 'source': '*', 'dest': 'idle'},
            { 'trigger': 'ResetAll', 'source': '*', 'dest': 'idle', 'before': 'release_all_resources'},
        ]

        Machine.__init__(self, states=states, transitions=transitions, send_event=True, initial='idle', on_exception='handle_error')

if __name__ == '__main__':
    opts, args = parseOptions()
    s2cs = S2CS(opts.s2_port, opts.app_port)

    while True:
        try:
            #  Wait for next request from S2UC or Prod/Cons App
            s2_request = s2cs.s2_svr_socket.recv()
            s2_message = pickle.loads(s2_request)
            print("Received S2UC request:", s2_message['cmd'])

            # Requesting resources
            if s2_message['cmd'] == 'REQ':
                s2cs.REQ(req=s2_message, tag="S2UC_REQ")
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

            # Updating targets
            elif s2_message['cmd'] == 'UpdateTargets':
                s2cs.UpdateTargets(req=s2_message, tag="S2UC_UPD")
                print("Current state: %s " % s2cs.state)
                s2cs.RESP()
                print("Current state: %s " % s2cs.state)

            # Releasing resources
            elif s2_message['cmd'] == 'REL':
                s2cs.REL(req=s2_message, tag="S2UC_REL", resp="Resources released")
                print("Current state: %s " % s2cs.state)
                # TODO: Signal to producer/consumer that request was released?
                s2cs.RESP()
                print("Current state: %s " % s2cs.state)

            # Error in request sent from S2UC
            elif s2_message['cmd'] == 'ERROR':
                s2cs.ERROR()
                print("Current state: %s " % s2cs.state)
                s2cs.ErrorRel(req=s2_message, tag="S2UC_ERR", resp="Resources released")

            # Unknown command
            else:
                s2cs.s2_svr_socket.send_string("ERROR: %s message not supported" % s2_message)

        # Error encountered in S2CS
        except AssertionError:
            print("ERROR: S2CS encountered AssertionError")
        except KeyboardInterrupt:
            s2cs.ResetAll()
            break
        except:
            print("ERROR: Unexpected error", sys.exc_info()[0])
            s2cs.ResetAll()
            break
