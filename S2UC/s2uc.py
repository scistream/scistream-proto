"""
    S2UC state machine implementation
"""

from transitions import Machine
from optparse import OptionParser
from itertools import cycle, islice
import time
import sys
import random
import zmq
import subprocess
import pickle
import logging
import json
import uuid
import os

#logging.basicConfig(level=logging.INFO)

# Parse command line options and dump results
def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option('--req-file', dest='req_file', default=None, help='JSON file with user request')
    (options, args) = parser.parse_args()

    return options, args

class S2UC(Machine):

    # Send request to reserve resources
    def send_req(self, event):
        req = event.kwargs.get('req')

        print("Requesting producer resources...")
        req["role"] = "PROD"
        self.prod_soc.send(pickle.dumps(req))

        print("Requesting consumer resources...")
        req["role"] = "CONS"
        self.cons_soc.send(pickle.dumps(req))

        # TODO: Temporary process to "spawn" ProdApp/ConsApp instances to send Hello requests
        origWD = os.getcwd()
        os.chdir(os.path.join(os.path.abspath(sys.path[0]), '../utils'))

        prod_app_listeners = ['127.0.0.1:7000', '127.0.0.1:17000']
        temp_prod_cli = ['python', 'send_hello.py', '--s2cs-port', '5500', '--uid', str(id)]
        for l in prod_app_listeners:
            temp_prod_cli.extend(['--prod-listener', l])
        subprocess.run(temp_prod_cli)
        subprocess.run(['python', 'send_hello.py', '--s2cs-port', '6500', '--uid', str(id)])
        os.chdir(origWD)

        self.prod_resp = pickle.loads(self.prod_soc.recv())
        self.cons_resp = pickle.loads(self.cons_soc.recv())
        print("Producer response:", self.prod_resp)
        print("Consumer response:", self.cons_resp)
        assert str(self.prod_resp)[:6] != "ERROR:", self.prod_resp
        assert str(self.cons_resp)[:6] != "ERROR:", self.cons_resp

        self.prod_lstn = self.prod_resp["listeners"]
        self.prod_app_lstn = self.prod_resp["prod_listeners"]
        self.cons_lstn = self.cons_resp["listeners"]

    # Send request to release resources
    def send_rel(self, event):
        req = event.kwargs.get('req')

        print("Releasing producer resources...")
        self.prod_soc.send(pickle.dumps(req))

        print("Releasing consumer resources...")
        self.cons_soc.send(pickle.dumps(req))

        self.prod_resp = pickle.loads(self.prod_soc.recv())
        self.cons_resp = pickle.loads(self.cons_soc.recv())
        print("Producer response: %s" % self.prod_resp)
        print("Consumer response: %s" % self.cons_resp)
        assert str(self.prod_resp)[:6] != "ERROR:", self.prod_resp
        assert str(self.cons_resp)[:6] != "ERROR:", self.cons_resp

    # Send updated target information from connection map
    def send_update_targets(self, event):
        # targets = event.kwargs.get('targets', None)
        # print("Updating targets: %s" % targets)

        uid = event.kwargs.get('uid', None)
        prod_req = {
                        "cmd": "UpdateTargets",
                        "uid": str(uid),
                        "local_listeners": self.prod_lstn,
                        "remote_listeners": self.prod_app_lstn
        }
        self.prod_soc.send(pickle.dumps(prod_req))

        cons_req = {
                        "cmd": "UpdateTargets",
                        "uid": str(uid),
                        "local_listeners": self.cons_lstn,
                        "remote_listeners": self.prod_lstn
        }
        self.cons_soc.send(pickle.dumps(cons_req))

        self.prod_resp = pickle.loads(self.prod_soc.recv())
        self.cons_resp = pickle.loads(self.cons_soc.recv())
        print("Producer response: %s" % self.prod_resp)
        print("Consumer response: %s" % self.cons_resp)
        assert str(self.prod_resp)[:6] != "ERROR:", self.prod_resp
        assert str(self.cons_resp)[:6] != "ERROR:", self.cons_resp

    # Create connection map to be used by S2CS
    def create_conn_map(self, event):
        # resp = event.kwargs.get('resp', None)
        # print("Key-value store update: %s" % resp)

        # TODO: If list sizes do not match, edit lists to evenly distribute resources (see s2cs.py itertools)
        print("Creating connection map...")
        print("Producer listeners: %s" % self.prod_lstn)
        print("ProdApp listeners: %s" % self.prod_app_lstn)
        print("Consumer listeners: %s" % self.cons_lstn)

    # Error handler
    def handle_error(self, event):
        print(event.error)
        raise AssertionError(event.error)

    # Initialize S2UC object
    def __init__(self, prod, cons):
        self.resp = None
        self.prod_lstn = None
        self.prod_app_lstn = None
        self.cons_lstn = None
        self.prod_resp = None
        self.cons_resp = None

        # Create client sockets
        prod_ctx = zmq.Context()
        print("Connecting to Producer S2CS...")
        self.prod_soc = prod_ctx.socket(zmq.REQ)
        self.prod_soc.connect("tcp://%s" % prod)

        cons_ctx = zmq.Context()
        print("Connecting to Consumer S2CS...")
        self.cons_soc = cons_ctx.socket(zmq.REQ)
        self.cons_soc.connect("tcp://%s" % cons)

        states = ['idle', 'reserving', 'provisioning', 'updating', 'releasing']

        transitions = [
            { 'trigger': 'SendReq', 'source': 'idle', 'dest': 'reserving', 'after': 'send_req'},
            { 'trigger': 'SendRel', 'source': 'idle', 'dest': 'releasing', 'after': 'send_rel'},
            { 'trigger': 'RESP', 'source': 'reserving', 'dest': None},
            { 'trigger': 'ProdLstn', 'source': 'reserving', 'dest': 'provisioning', 'before': 'create_conn_map'},
            { 'trigger': 'SendUpdateTargets', 'source': 'provisioning', 'dest': 'updating', 'after': 'send_update_targets'},
            { 'trigger': 'RESP', 'source': ['updating', 'releasing'], 'dest': 'idle'},
            { 'trigger': 'ERROR', 'source': '*', 'dest': 'releasing'},
            { 'trigger': 'ErrorRel', 'source': 'releasing', 'dest': 'idle'},
        ]

        Machine.__init__(self, states=states, transitions=transitions, send_event=True, initial='idle', on_exception='handle_error')

if __name__ == '__main__':
    start = time.time()
    opts, args = parseOptions()

    if opts.req_file != None:
        with open(opts.req_file, 'r') as f:
            request = json.load(f)
        s2uc = S2UC(prod=request['prod'], cons=request['cons'])
    else:
        sys.exit("Please provide a JSON file with your request.")

    try:
        if request['cmd'] == 'REQ':
            # User request
            id = uuid.uuid1()
            req = {
                    'cmd': request['cmd'],
                    'uid': str(id),
                    'num_conn': request['num_conn'],
                    'rate': request['rate']
            }
            print("Sending request:", req)
            s2uc.SendReq(req=req)
            print("Current state: %s " % s2uc.state)

            s2uc.ProdLstn()
            print("Current state: %s " % s2uc.state)

            s2uc.SendUpdateTargets(uid=id)
            print("Current state: %s " % s2uc.state)
            s2uc.RESP(resp="Targets updated")
            print("Current state: %s " % s2uc.state)
            t = time.time() - start
            print("*** Process time: %s sec." % t)

        elif request['cmd'] == 'REL':
            # Release request
            req = {
                    'cmd': request['cmd'],
                    'uid': request['uid']
            }
            s2uc.SendRel(req=req)
            print("Current state: %s " % s2uc.state)
            s2uc.RESP(resp="Resources released")
            print("Current state: %s " % s2uc.state)
            t = time.time() - start
            print("*** Process time: %s sec." % t)

        else:
            t = time.time() - start
            print("*** Process time: %s sec." % t)
            sys.exit("Unrecognized command, please use REQ or REL")
    except AssertionError as err:
        print("ERROR: S2UC encountered AssertionError")
    except:
        print("ERROR: Unexpected error", sys.exc_info()[0])
        # TODO: Release all resources
