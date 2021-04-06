"""
    S2CS state machine implementation
"""

from transitions import Machine
from time import sleep
from optparse import OptionParser
import random
import zmq
import pickle

# Parse command line options and dump results
def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option('--svr-port', dest='svr_port', default="5000", help='S2CS server port')
    parser.add_option('--clt-port', dest='clt_port', default="5001", help='Remote S2DS port')
    (options, args) = parser.parse_args()

    return options, args

class S2CS(Machine):
    def update_kvs(self, event):
        tag = event.kwargs.get('tag', None)

        if tag == "S2UC_REQ":
            req = event.kwargs.get('req', None)
            entry = {
                      "role": req['role'],
                      "num_conn": req['num_conn'],
                      "rate": req['rate']
            }
            self.kvs[req["uid"]] = entry
            print("Key-value store update: %s" % self.kvs)
        elif tag == "S2DS_RESP":
            pass
        else:
            print("Unrecognized message")

    def fwd_msg(self, event):
        req = event.kwargs.get('req', None)
        info = event.kwargs.get('info', None)
        print(info)
        self.clt_socket.send(pickle.dumps(req))
        self.resp = self.clt_socket.recv()

    def send_prod_lstn(self, event):
        req = event.kwargs.get('req', None)
        entry = self.kvs[req["uid"]]
        if entry["role"] == "PROD":
            self.svr_socket.send_string("Sending Prod listeners...")
        else:
            self.svr_socket.send_string("I'm Cons, nothing to send.")

    def send_resp(self, event):
        #resp = event.kwargs.get('resp', None)
        self.svr_socket.send(self.resp)

    def send_ack(self, event):
        print("ACK")

    def __init__(self, svr_port, clt_port):
        self.kvs = {}
        self.resp = None

        # Create S2CS server side
        svr_context = zmq.Context()
        self.svr_socket = svr_context.socket(zmq.REP)
        self.svr_socket.bind("tcp://*:%s" % svr_port)
        print("S2CS server running on port TCP/%s" % svr_port)

        # Create client for S2DS
        clt_context = zmq.Context()
        print("Connecting to S2DS...")
        self.clt_socket = clt_context.socket(zmq.REQ)
        self.clt_socket.connect("tcp://localhost:%s" % clt_port)

        states = ['idle', 'reserving', 'listening', 'updating', 'releasing']

        transitions = [
            { 'trigger': 'REQ', 'source': 'idle', 'dest': 'reserving', 'before': 'update_kvs', 'after': 'fwd_msg'},
            { 'trigger': 'RESP', 'source': 'reserving', 'dest': 'listening', 'before': 'update_kvs', 'after': 'send_resp'},
            { 'trigger': 'Hello', 'source': 'listening', 'dest': 'idle', 'before': 'send_prod_lstn', 'after': 'send_ack'},
            { 'trigger': 'REL', 'source': 'idle', 'dest': 'releasing', 'before': 'update_kvs', 'after': 'fwd_msg'},
            { 'trigger': 'RESP', 'source': 'releasing', 'dest': 'idle', 'before': 'update_kvs', 'after': 'send_resp'},
            { 'trigger': 'UpdateTargets', 'source': 'idle', 'dest': 'updating', 'before': 'update_kvs', 'after': 'fwd_msg'},
            { 'trigger': 'RESP', 'source': 'updating', 'dest': 'idle', 'before': 'update_kvs', 'after': 'send_resp'},
            { 'trigger': 'ERROR', 'source': ['reserving', 'listening', 'updating'], 'dest': 'releasing'},
            { 'trigger': 'ErrorRel', 'source': 'releasing', 'dest': 'idle', 'before': 'update_kvs', 'after': 'send_resp'},
        ]

        Machine.__init__(self, states=states, transitions=transitions, send_event=True, initial='idle')

if __name__ == '__main__':
    opts, args = parseOptions()
    s2cs = S2CS(opts.svr_port, opts.clt_port)

    while True:
        #  Wait for next request from S2UC or Prod/Cons App
        request = s2cs.svr_socket.recv()
        message = pickle.loads(request)
        print("Received request: ", message['cmd'])

        if message['cmd'] == 'REQ':
            s2cs.REQ(req=message, tag="S2UC_REQ", info="Requesting resources...")
            print("Current state: %s " % s2cs.state)
            s2cs.RESP(tag="S2DS_RESP")
            print("Current state: %s " % s2cs.state)

        elif message['cmd'] == 'Hello':
            s2cs.Hello(req=message)
            print("Current state: %s " % s2cs.state)

        elif message['cmd'] == 'UpdateTargets':
            # Testing UpdateTargets
            s2cs.UpdateTargets(req=message, info="Targets: A --> B")
            print("Current state: %s " % s2cs.state)
            s2cs.RESP()
            print("Current state: %s " % s2cs.state)

        elif message['cmd'] == 'REL':
            # Testing User REL
            s2cs.REL(req=message, info="Releasing resources...")
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
