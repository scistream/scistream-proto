"""
    S2DS state machine implementation
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
    parser.add_option('--port', dest='port', default="5001", help='S2DS server port')
    (options, args) = parser.parse_args()

    return options, args

class S2DS(Machine):
    def reserve_resources(self, event):
        req = event.kwargs.get('req', None)
        listeners = []
        print("Reserving S2DS resources...")

        if req["role"] == "PROD":
            pool = "5000"
        else:
            pool = "6000"

        if req["num_conn"] > 1:
            for i in range(req["num_conn"]):
                listeners.append("localhost:%s%s" % (pool, i))
        else:
            listeners.append("localhost:%s0" % pool)

        self.resp = listeners

    def release_resources(self, event):
        print("Releasing S2DS resources...")
        self.resp = "Resources released"

    def update_targets(self, event):
        print("Updating targets...")
        self.resp = "Targets updated"

    def send_resp(self, event):
        self.socket.send(pickle.dumps(self.resp))

    def __init__(self, port):
        self.kvs = {}
        self.resp = None
        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.bind("tcp://*:%s" % port)
        print("S2DS server running on port TCP/%s" % port)

        states = ['idle', 'reserving', 'updating', 'releasing']

        transitions = [
            { 'trigger': 'REQ', 'source': 'idle', 'dest': 'reserving', 'after': 'reserve_resources'},
            { 'trigger': 'UpdateTargets', 'source': 'idle', 'dest': 'updating', 'after': 'update_targets'},
            { 'trigger': 'REL', 'source': 'idle', 'dest': 'releasing', 'after': 'release_resources'},
            { 'trigger': 'SendResp', 'source': ['reserving', 'updating', 'releasing'], 'dest': 'idle', 'before': 'send_resp'}
        ]

        Machine.__init__(self, states=states, transitions=transitions, send_event=True, initial='idle')

if __name__ == '__main__':
    opts, args = parseOptions()
    s2ds = S2DS(opts.port)

    while True:
        #  Wait for next request from client
        request = s2ds.socket.recv()
        message = pickle.loads(request)
        print("Received request: ", message)

        if message['cmd'] == 'REQ':
            # Testing REQ
            s2ds.REQ(req=message)
            print("Current state: %s " % s2ds.state)
            s2ds.SendResp()
            print("Current state: %s " % s2ds.state)

        elif message['cmd'] == 'UpdateTargets':
            # Testing UpdateTargets
            s2ds.UpdateTargets()
            print("Current state: %s " % s2ds.state)
            s2ds.SendResp()
            print("Current state: %s " % s2ds.state)

        elif message['cmd'] == 'REL':
            # Testing REL
            s2ds.REL()
            print("Current state: %s " % s2ds.state)
            s2ds.SendResp()
            print("Current state: %s " % s2ds.state)

        else:
            s2ds.socket.send_string("RESP: %s message not supported" % message)
