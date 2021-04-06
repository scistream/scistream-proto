import zmq
import sys
import pickle

if len(sys.argv) > 1:
    message = {"cmd": str(sys.argv[1])}
else:
    message = {"cmd": "REQ"}

port = "5000"
context = zmq.Context()
print("Connecting to server...")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:%s" % port)

print("Sending request %s" % message)
socket.send(pickle.dumps(message))
resp = socket.recv_string()
print("Received reply: %s" % resp)
