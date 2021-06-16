import zmq
import sys
import pickle
from optparse import OptionParser

# Parse command line options and dump results
def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option('--port', dest='port', default="5000", help='S2CS server port')
    parser.add_option('--uid', dest='uid', default=None, help='Request\'s unique id')
    parser.add_option('--listeners', dest='listeners', default=None, help="Port listeners used by ProdAPP")
    (options, args) = parser.parse_args()
    return options, args

opts, args = parseOptions()

message = {"cmd": "Hello", "uid": opts.uid, "listeners": opts.listeners}
context = zmq.Context()
print("Connecting to server...")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:%s" % opts.port)

print("Sending Hello...")
socket.send(pickle.dumps(message))
resp = socket.recv_string()
print("Received reply: %s" % resp)
