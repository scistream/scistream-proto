"""
    S2DS state machine implementation
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
            self.is_prod = True
        else:
            pool = "4000"

        if req["num_conn"] > 1:
            for i in range(req["num_conn"]):
                listeners.append("localhost:%s%s" % (pool, i))
        else:
            listeners.append("localhost:%s0" % pool)

        self.resp = listeners

    def release_resources(self, event):
        print("Releasing S2DS resources...")
        if (self.s2ds_proc != None):
            self.s2ds_proc.terminate()
            self.s2ds_proc = None
            print("Terminated S2DS subprocess")

        self.resp = "Resources released"

    def bind_prod_listeners(self, event):
        assert self.is_prod == True, "Consumer S2DS received Hello message to bind listeners"
        req = event.kwargs.get('req', None)
        print("Binding Prod listeners...")
        # TODO: Check if ports are open
        self.prod_listener = req["prod_listeners"]
        print("Binded Prod listeners %s " % self.prod_listener) # TODO: Not actually bound, but don't think it's possible here...

    def update_targets(self, event):
        print("Updating targets...")
        req = event.kwargs.get('req', None)

        # TODO: Combine repos for reliable relative path
        # TODO: Change logic to allow for more than one S2DS subprocess
        if (self.is_prod):
            assert self.s2ds_proc == None, "S2DS subprocess already launched!"
            assert self.prod_listener != None, "Prod S2CS never received or never forwarded ProdApp Hello to Prod S2DS"
            origWD = os.getcwd()
            os.chdir(os.path.join(os.path.abspath(sys.path[0]), '../../scistream/S2DS'))
            self.s2ds_proc = subprocess.Popen(['./S2DS.out', '--remote-port', self.prod_listener, '--local-port', str(req["local_port"]), '--remote-host', '127.0.0.1'])
            os.chdir(origWD)
            print("Starting S2DS subprocess with local-port %s and remote-port %s..." % (req["local_port"], self.prod_listener))
        else:
            assert self.s2ds_proc == None, "S2DS subprocess already launched!"
            origWD = os.getcwd()
            os.chdir(os.path.join(os.path.abspath(sys.path[0]), '../../scistream/S2DS'))
            self.s2ds_proc = subprocess.Popen(['./S2DS.out', '--remote-port', str(req["remote_port"]), '--local-port', str(req["local_port"]), '--remote-host', '127.0.0.1'])
            os.chdir(origWD)
            print("Starting S2DS subprocess with local-port %s and remote-port %s..." % (req["remote_port"], req["local_port"]))
            print("INFO:", event.kwargs)
        print("Targets updated")
        self.resp = "Targets updated"

    def send_resp(self, event):
        self.socket.send(pickle.dumps(self.resp))

    def __init__(self, port):
        self.kvs = {} # Dictionary: UUID -> Request
        self.resp = None # Response message used in send_resp
        self.s2ds_proc = None # Process information for spawned s2ds "buffer-and-forward" process(es)
        self.is_prod = False # Flag for if S2DS is at producer or consumer
        self.prod_listener = None # Remote-port of ProdApp for the producer S2DS to connect to
        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.bind("tcp://*:%s" % port)
        print("S2DS server running on port TCP/%s" % port)

        states = ['idle', 'reserving', 'updating', 'releasing']

        transitions = [
            { 'trigger': 'REQ', 'source': 'idle', 'dest': 'reserving', 'after': 'reserve_resources'},
            { 'trigger': 'Hello', 'source': 'idle', 'dest': 'updating', 'after': 'bind_prod_listeners'},
            { 'trigger': 'UpdateTargets', 'source': 'idle', 'dest': 'updating', 'after': 'update_targets'},
            { 'trigger': 'REL', 'source': 'idle', 'dest': 'releasing', 'after': 'release_resources'},
            { 'trigger': 'SendResp', 'source': ['reserving', 'updating', 'releasing'], 'dest': 'idle', 'before': 'send_resp'}
        ]

        Machine.__init__(self, states=states, transitions=transitions, send_event=True, initial='idle')

if __name__ == '__main__':
    opts, args = parseOptions()
    s2ds = S2DS(opts.port)

    def signal_handler(signum, frame):
        signal.signal(signum, signal.SIG_IGN) # Ignore duplicate signals
        if (s2ds.s2ds_proc != None):
            s2ds.s2ds_proc.terminate()
            s2ds.s2ds_proc = None
            print("Terminated S2DS subprocess...")
        print("Exiting...")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

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

        elif message['cmd'] == 'Hello':
            # Testing Hello
            s2ds.Hello(req=message)
            print("Current state: %s " % s2ds.state)
            s2ds.SendResp()
            print("Current state: %s " % s2ds.state)

        elif message['cmd'] == 'UpdateTargets':
            # Testing UpdateTargets
            s2ds.UpdateTargets(req=message)
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
