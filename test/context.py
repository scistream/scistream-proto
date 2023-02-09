import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import S2UC.s2uc as s2uc
import pickle

# Mock the following function
CONS_REPLY = {'listeners': ['127.0.0.1:41561', '127.0.0.1:44775', '127.0.0.1:42731', '127.0.0.1:33845', '127.0.0.1:46843']}
PROD_RESP = {
    'listeners': ['127.0.0.1:37871', '127.0.0.1:44009', '127.0.0.1:43045', '127.0.0.1:37551', '127.0.0.1:36733'],
    'prod_listeners': ['127.0.0.1:7000', '127.0.0.1:17000', '127.0.0.1:27000', '127.0.0.1:37000', '127.0.0.1:47000']
    }
UpdateTargets = "Targets updated"
class mocksocket():
    def __init__(self):
        self.queue = []

    def send(self,msg):
        input = pickle.loads(msg)
        if input['cmd'] == 'REQ':
            if input['role'] == "PROD":
                output = PROD_RESP
            if input['role'] == "CONS":
                output = CONS_REPLY
        if input['cmd'] == 'REL':
            output = UpdateTargets
        if input['cmd'] == 'Hello':
            output = "Resources released"
        if input['cmd'] == 'UpdateTargets':
            output = UpdateTargets
        self.queue.append(pickle.dumps(output))
        return

    def recv(self):
        return self.queue.pop()

    def close(self):
        return
