"""
    S2CS state machine implementation
"""

from transitions import Machine
from time import sleep
import random

class S2CS(Machine):
    def update_kvs(self):
        print("Key-value store updated")

    def clear_kvs(self):
        print("Key-value store cleared")

    def reserve_resources(self):
        print("Reserving: Contacting S2DS...")
        return random.random() < 0.5

    def release_resources(self):
        print("Releasing: Contacting S2DS...")

    def commit_resources(self):
        print("Creating connection map and data connection credentials")

    def start_s2ds(self):
        print("Starting S2DS...")

    def __init__(self):
        states = ['idle', 'waiting', 'reserving', 'provisioning', 'streaming', 'releasing']

        transitions = [
            { 'trigger': 'S2ucReq', 'source': 'idle', 'dest': 'waiting', 'after': 'update_kvs'},
            { 'trigger': 'Hello', 'source': 'waiting', 'dest': 'reserving', 'conditions': 'reserve_resources'},
            { 'trigger': 'Hello', 'source': 'waiting', 'dest': 'idle', 'before': 'clear_kvs'},
            { 'trigger': 'Update', 'source': 'reserving', 'dest': 'provisioning', 'after': 'start_s2ds'},
            { 'trigger': 'StartStreaming', 'source': 'provisioning', 'dest': 'streaming'},
            { 'trigger': 'StopStreaming', 'source': 'streaming', 'dest': 'releasing', 'after': 'release_resources'},
            { 'trigger': 'Released', 'source': 'releasing', 'dest': 'idle', 'before': 'clear_kvs'}
        ]

        Machine.__init__(self, states=states, transitions=transitions, initial='idle')

if __name__ == '__main__':
    s2cs = S2CS()
    s2cs.S2ucReq()
    s2cs.Hello()
    if s2cs.state == 'reserving':
        s2cs.Update()
        print(s2cs.state)
        s2cs.StartStreaming()
        print(s2cs.state)
        sleep(random.randint(0,5))
        s2cs.StopStreaming()
        print(s2cs.state)
        s2cs.Released()
    print(s2cs.state)
