import zmq
import sys
import pickle
from optparse import OptionParser

# Parse command line options and dump results
def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option('--s2cs-port', dest='s2cs_port', default="5500", help='ProdApp/ConsApp->S2CS server port')
    parser.add_option('--uid', dest='uid', default=None, help='Request\'s unique id')
    parser.add_option('--prod-listeners', dest='prod_listeners', default=None, help="ProdApp listeners")
    (options, args) = parser.parse_args()
    return options, args

opts, args = parseOptions()

if (opts.prod_listeners != None):
    message = {"cmd": "Hello", "uid": opts.uid, "prod_listeners": opts.prod_listeners}
else:
    message = {"cmd": "Hello", "uid": opts.uid}
context = zmq.Context()
print("send_hello.py: Connecting to server...")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:%s" % opts.s2cs_port)

print("send_hello.py: Sending Hello...")
socket.send(pickle.dumps(message))
resp = socket.recv_string()
print("send_hello.py: Received reply: %s" % resp)
