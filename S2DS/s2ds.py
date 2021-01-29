"""
    S2DS state machine implementation
"""

from transitions import Machine
from time import sleep
import random

class S2DS(Machine):
    def reserve_resources(self):
        print("Reserving S2DS resources...")
        return random.random() < 0.5

    def release_resources(self):
        print("Releasing S2DS resources...")

    def start_listners(self):
        print("Starting S2DS listeners...")

    def send_error_msg(self):
        print("ERROR...")

    def __init__(self):
        states = ['idle', 'reserving', 'listening', 'streaming', 'releasing']

        transitions = [
            { 'trigger': 'LstnrReq', 'source': 'idle', 'dest': 'reserving', 'conditions': 'reserve_resources'},
            { 'trigger': 'LstnrReq', 'source': 'idle', 'dest': None, 'before': 'send_error_msg'},
            { 'trigger': 'StartListeners', 'source': 'reserving', 'dest': 'listening', 'before': 'start_listners'},
            { 'trigger': 'Connect', 'source': 'listening', 'dest': 'streaming'},
            { 'trigger': 'StopStreaming', 'source': 'streaming', 'dest': 'releasing', 'after': 'release_resources'},
            { 'trigger': 'Released', 'source': 'releasing', 'dest': 'idle'}
        ]

        Machine.__init__(self, states=states, transitions=transitions, initial='idle')

if __name__ == '__main__':
    s2ds = S2DS()
    s2ds.LstnrReq()
    if s2ds.state == 'reserving':
        s2ds.StartListeners()
        print(s2ds.state)
        s2ds.Connect()
        print(s2ds.state)
        sleep(random.randint(0,5))
        s2ds.StopStreaming()
        print(s2ds.state)
        s2ds.Released()
    print(s2ds.state)
