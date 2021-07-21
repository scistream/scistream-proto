from optparse import OptionParser
import zmq
import sys
import pickle
import logging

send_hello_logger = logging.getLogger("send_hello.py")

# Parse command line options and dump results
def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option('--s2cs-port', dest='s2cs_port', default="5500", help='ProdApp/ConsApp->S2CS server port')
    parser.add_option('--uid', dest='uid', default=None, help='Request\'s unique id')
    parser.add_option('--prod-listener', dest='prod_listeners', default=[], action='append', help="ProdApp listener")
    parser.add_option("--v", action="store_true", dest="verbose", default=False, help="Verbose output")
    (options, args) = parser.parse_args()
    return options, args

opts, args = parseOptions()
if opts.verbose:
    formatter = logging.Formatter(fmt="send_hello.py: %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    send_hello_logger.addHandler(handler)
    send_hello_logger.setLevel(logging.INFO)

if (opts.prod_listeners != []):
    message = {"cmd": "Hello", "uid": opts.uid, "prod_listeners": opts.prod_listeners}
else:
    message = {"cmd": "Hello", "uid": opts.uid}
context = zmq.Context()
send_hello_logger.info("Connecting to server...")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:%s" % opts.s2cs_port)

print("send_hello.py: Sending Hello...")
socket.send(pickle.dumps(message))
resp = socket.recv_string()
send_hello_logger.info("Received reply: %s" % resp)
