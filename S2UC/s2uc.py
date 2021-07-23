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
import threading

threads = {}
thread_mutex = threading.RLock()
s2uc_logger = logging.getLogger("s2uc.py")

# Parse command line options and dump results
def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option("--v", action="store_true", dest="verbose", default=False, help="Verbose output")
    # parser.add_option('--req-file', dest='req_file', default=None, help='JSON file with user request')
    (options, args) = parser.parse_args()

    return options, args

class S2UC(Machine):

    # Send request to reserve resources
    def send_req(self, event):
        req = event.kwargs.get('req', None)
        uid = req.get("uid", None)
        assert uid != None and uid != "", "Invalid uid '%s'" % uid

        print("Requesting producer resources...")
        req["role"] = "PROD"
        self.prod_soc.send(pickle.dumps(req))

        print("Requesting consumer resources...")
        req["role"] = "CONS"
        self.cons_soc.send(pickle.dumps(req))

        # TODO: Temporary process to "spawn" ProdApp/ConsApp instances to send Hello requests
        origWD = os.getcwd()
        os.chdir(os.path.join(os.path.abspath(sys.path[0]), '../utils'))

        # TODO: Remove hard-coded prod_app_listeners and ProdApp->S2CS ports
        prod_app_listeners = ['127.0.0.1:7000', '127.0.0.1:17000', '127.0.0.1:27000', '127.0.0.1:37000', '127.0.0.1:47000']
        temp_prod_cli = ['python', 'send_hello.py', '--s2cs-port', self.prod_app_port, '--uid', str(uid)]
        for l in prod_app_listeners:
            temp_prod_cli.extend(['--prod-listener', l])
        temp_cons_cli = ['python', 'send_hello.py', '--s2cs-port', self.cons_app_port, '--uid', str(uid)]
        if opts.verbose:
            temp_prod_cli.extend(['--v'])
            temp_cons_cli.extend(['--v'])
        subprocess.run(temp_prod_cli)
        subprocess.run(temp_cons_cli)
        os.chdir(origWD)

        self.prod_resp = pickle.loads(self.prod_soc.recv())
        self.cons_resp = pickle.loads(self.cons_soc.recv())
        s2uc_logger.info("Producer response: %s" % self.prod_resp)
        s2uc_logger.info("Consumer response: %s" % self.cons_resp)
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
        s2uc_logger.info("Producer response: %s" % self.prod_resp)
        s2uc_logger.info("Consumer response: %s" % self.cons_resp)
        assert str(self.prod_resp)[:6] != "ERROR:", self.prod_resp
        assert str(self.cons_resp)[:6] != "ERROR:", self.cons_resp

    # Send updated target information from connection map
    def send_update_targets(self, event):
        # targets = event.kwargs.get('targets', None)
        # print("Updating targets: %s" % targets)
        req = event.kwargs.get('req', None)
        uid = req.get("uid", None)
        assert uid != None and uid != "", "Invalid uid '%s'" % uid

        print("Sending updated connection map information...")

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
        s2uc_logger.info("Producer response: %s" % self.prod_resp)
        s2uc_logger.info("Consumer response: %s" % self.cons_resp)
        assert str(self.prod_resp)[:6] != "ERROR:", self.prod_resp
        assert str(self.cons_resp)[:6] != "ERROR:", self.cons_resp

        print("Connection map information successfully updated")

    # Create connection map to be used by S2CS
    def create_conn_map(self, event):
        # resp = event.kwargs.get('resp', None)
        # print("Key-value store update: %s" % resp)

        # TODO: If list sizes do not match, edit lists to evenly distribute resources (see s2cs.py itertools)
        print("Creating connection map...")
        s2uc_logger.info("ProdApp listeners: %s" % self.prod_app_lstn)
        s2uc_logger.info("Producer S2DS listeners: %s" % self.prod_lstn)
        s2uc_logger.info("Consumer S2DS listeners: %s" % self.cons_lstn)

    # Error handler
    def handle_error(self, event):
        # Receive any messages first (non-blocking)
        err_msg = event.error
        print(err_msg)

        if (event.event.name == "SendRel" or event.event.name == "ErrorRel"):
            self.Reset()
            raise AssertionError("ERROR: S2UC encountered error while attempting to release S2CS resources")

        self.ERROR()
        req = event.kwargs.get('req', None)
        uid = req.get("uid", None)
        if uid == None or uid == "":
            raise AssertionError("ERROR: Invalid uid '%s'" % uid)

        error_req = {
                'cmd': "ERROR",
                'uid': req["uid"]
        }
        print("Sending error release request for uid '%s'..." % req["uid"])
        self.ErrorRel(req=error_req)
        raise AssertionError(err_msg)

    # Initialize S2UC object
    def __init__(self, prod, cons):
        self.resp = None
        self.prod_lstn = None
        self.prod_app_lstn = None
        self.cons_lstn = None
        self.prod_resp = None
        self.cons_resp = None

        # TODO: Allow this to be configurable?
        self.prod_app_port = '5500' # ProdApp->S2CS port
        self.cons_app_port = '6500' # ConsApp->S2CS port

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
            { 'trigger': 'RESP', 'source': 'reserving', 'dest': 'idle'},
            { 'trigger': 'ProdLstn', 'source': 'reserving', 'dest': 'provisioning', 'before': 'create_conn_map'},
            { 'trigger': 'SendUpdateTargets', 'source': 'provisioning', 'dest': 'updating', 'after': 'send_update_targets'},
            { 'trigger': 'RESP', 'source': ['updating', 'releasing'], 'dest': 'idle'},
            { 'trigger': 'ERROR', 'source': '*', 'dest': 'releasing'},
            { 'trigger': 'ErrorRel', 'source': 'releasing', 'dest': 'idle', 'after': 'send_rel'},
            { 'trigger': 'Reset', 'source': '*', 'dest': 'idle'}
        ]

        Machine.__init__(self, states=states, transitions=transitions, send_event=True, initial='idle', on_exception='handle_error')

def new_s2uc_request(req_file):
    start = time.time()

    with thread_mutex:
        threads[threading.current_thread()] = {}

    if req_file != None:
        try:
            origWD = os.getcwd() # TODO: Better way to find files?
            os.chdir(os.path.abspath(sys.path[0]))
            with open(req_file, 'r') as f:
                request = json.load(f)
            os.chdir(origWD)
            s2uc = S2UC(prod=request['prod'], cons=request['cons'])
            with thread_mutex:
                threads[threading.current_thread()] = request
        except OSError as err:
            print("ERROR:", err)
            sys.exit(err)
        except:
            print("ERROR: Unexpected error: %s" % sys.exc_info()[0])
            sys.exit("ERROR: Unexpected error")
    else:
        sys.exit("ERROR: Please provide a JSON file with your request.")

    try:
        # Process user request
        if request['cmd'] == 'REQ':
            # User request
            cmd = request.get("cmd", None)
            id = uuid.uuid1()
            num_conn = request.get("num_conn", None)
            rate = request.get("rate", None)
            assert cmd != None and cmd != "", "Invalid command '%s'" % cmd
            assert num_conn != None and int(num_conn) > 0, "Invalid number of connections '%s'" % num_conn
            assert rate != None and int(rate) > 0, "Invalid rate '%s'" % rate
            req = {
                    'cmd': cmd,
                    'uid': str(id),
                    'num_conn': num_conn,
                    'rate': rate
            }
            # TODO: Return uid, prod_app_port, and cons_app_port to "user" application
            if opts.verbose:
                s2uc_logger.info("Sending request: %s" % req)
                s2uc_logger.info("ProdApp->S2CS port: %s" % s2uc.prod_app_port)
                s2uc_logger.info("ConsApp->S2CS port: %s" % s2uc.cons_app_port)
            else:
                print("Sending request with uid '%s'" % str(id))
            s2uc.SendReq(req=req)
            s2uc_logger.info("Current state: %s " % s2uc.state)

            s2uc.ProdLstn(req=req)
            s2uc_logger.info("Current state: %s " % s2uc.state)

            s2uc.SendUpdateTargets(req=req)
            s2uc_logger.info("Current state: %s " % s2uc.state)
            s2uc.RESP()
            s2uc_logger.info("Current state: %s " % s2uc.state)
            t = time.time() - start
            print("*** Process time: %s sec." % t)

        elif request['cmd'] == 'REL':
            # Release request
            cmd = request.get("cmd", None)
            uid = request.get("uid", None)
            assert cmd != None and cmd != "", "Invalid command '%s'" % cmd
            assert uid != None and uid != "", "Invalid uid '%s'" % uid

            req = {
                    'cmd': cmd,
                    'uid': uid
            }
            if opts.verbose:
                s2uc_logger.info("Sending release: %s" % req)
            else:
                print("Sending release with uid '%s'" % uid)
            s2uc.SendRel(req=req)
            s2uc_logger.info("Current state: %s " % s2uc.state)
            s2uc.RESP()
            s2uc_logger.info("Current state: %s " % s2uc.state)
            t = time.time() - start
            print("*** Process time: %s sec." % t)

        else:
            t = time.time() - start
            print("*** Process time: %s sec." % t)
            sys.exit("Unrecognized command, please use REQ or REL")

    # Error encountered in S2UC
    except AssertionError as err:
        print(err)
    except KeyboardInterrupt:
        pass
    except:
        print("ERROR: Unexpected error: %s" % sys.exc_info()[0])

    # TODO: Temporary message since thread output may hide input prompt
    print("\nEnter user request file name:")

if __name__ == '__main__':
    opts, args = parseOptions()
    if opts.verbose:
        formatter = logging.Formatter(fmt="%(message)s")
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        s2uc_logger.addHandler(handler)
        s2uc_logger.setLevel(logging.INFO)

    while True:
        try:
            req_file = input("\nEnter user request file name:\n")
            if (req_file == ""):
                continue
            new_thread = threading.Thread(target=new_s2uc_request, args=(req_file,))
            new_thread.start()
        except KeyboardInterrupt:
            break
        except:
            print("ERROR: Unexpected error: %s" % sys.exc_info()[0])
            break

    try:
        for t, info in threads.items():
            s2uc_logger.info("Joining thread '%s' for req '%s'" % (t.ident, info))
            t.join()
    except:
        print("ERROR: Unexpected error: %s" % sys.exc_info()[0])
