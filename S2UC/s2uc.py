"""
    S2UC state machine implementation
"""

from transitions import Machine
from optparse import OptionParser
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
    def send_req(self, event):
        req = event.kwargs.get('req')

        print("Requesting producer resources...")
        req["role"] = "PROD"
        self.prod_soc.send(pickle.dumps(req))
        self.prod_lstn = pickle.loads(self.prod_soc.recv())

        print("Requesting consumer resources...")
        req["role"] = "CONS"
        self.cons_soc.send(pickle.dumps(req))
        self.cons_lstn = pickle.loads(self.cons_soc.recv())

    def send_rel(self, event):
        req = event.kwargs.get('req')

        print("Releasing producer resources...")
        self.prod_soc.send(pickle.dumps(req))
        self.prod_resp = pickle.loads(self.prod_soc.recv())

        print("Releasing consumer resources...")
        self.cons_soc.send(pickle.dumps(req))
        self.cons_resp = pickle.loads(self.cons_soc.recv())

        print("Producer response: %s" % self.prod_resp)
        print("Consumer response: %s" % self.cons_resp)

    def send_update_targets(self, event):
        # targets = event.kwargs.get('targets', None)
        # print("Updating targets: %s" % targets)

        # TODO: Find a better way to send ports and possible "remote-hosts" as well
        prod_req = {"cmd": "UpdateTargets", "local_port": str(self.prod_lstn[0].split(":")[1])}
        self.prod_soc.send(pickle.dumps(prod_req))
        self.prod_resp = pickle.loads(self.prod_soc.recv())
        print("Producer response: %s" % self.prod_resp)

        cons_req = {"cmd": "UpdateTargets", "local_port": str(self.cons_lstn[0].split(":")[1]), "remote_port": str(self.prod_lstn[0].split(":")[1])}
        self.cons_soc.send(pickle.dumps(cons_req))
        self.cons_resp = pickle.loads(self.cons_soc.recv())
        print("Consumer response: %s" % self.cons_resp)

    def create_conn_map(self, event):
        # resp = event.kwargs.get('resp', None)
        # print("Key-value store update: %s" % resp)
        print("Creating connection map...")
        print("Producer listeners: %s" % self.prod_lstn)
        print("Consumer listeners: %s" % self.cons_lstn)

    def __init__(self, prod, cons):
        self.resp = None
        self.prod_lstn = None
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
            { 'trigger': 'ERROR', 'source': ['reserving', 'provisioning', 'updating'], 'dest': 'releasing'},
            { 'trigger': 'RESP', 'source': ['updating', 'releasing'], 'dest': 'idle'},
            { 'trigger': 'ErrorRel', 'source': 'releasing', 'dest': 'idle'},
        ]

        Machine.__init__(self, states=states, transitions=transitions, send_event=True, initial='idle')

if __name__ == '__main__':
    start = time.time()
    opts, args = parseOptions()

    if opts.req_file != None:
        with open(opts.req_file, 'r') as f:
            request = json.load(f)
        s2uc = S2UC(prod=request['prod'], cons=request['cons'])
    else:
        sys.exit("Please provide a JSON file with your request.")

    if request['cmd'] == 'REQ':
        # User request
        id = uuid.uuid1()
        req = {
                'cmd': request['cmd'],
                'uid': str(id),
                'num_conn': request['num_conn'],
                'rate': request['rate']
        }
        s2uc.SendReq(req=req)
        print("Current state: %s " % s2uc.state)

        # TODO: Temporary process to "spawn" ProdApp/ConsApp instances to send Hello requests
        origWD = os.getcwd()
        os.chdir(os.path.join(os.path.abspath(sys.path[0]), '../utils'))
        temp_prod_listeners = '7000'
        subprocess.run(['python', 'send_hello.py', '--s2cs-port', '5000', '--uid', str(id), '--prod-listeners', temp_prod_listeners])
        subprocess.run(['python', 'send_hello.py', '--s2cs-port', '6000', '--uid', str(id)])
        os.chdir(origWD)

        # TODO: Should come from producer S2CS after it receives 'Hello' from ProdApp
        s2uc.ProdLstn(listeners=temp_prod_listeners)
        print("Current state: %s " % s2uc.state)

        s2uc.SendUpdateTargets()
        print("Current state: %s " % s2uc.state)
        s2uc.RESP(resp="Targets updated")
        print("Current state: %s " % s2uc.state)
        t = time.time() - start
        print("*** Process time: %s sec." % t)

    elif request['cmd'] == 'REL':
        # Release request
        # TODO: Signal to producer/consumer that request was released?
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
