"""
    S2UC state machine implementation
"""

from transitions import Machine
from time import sleep
import random

class S2UC(Machine):
    def reserve_resources(self):
        print("Reserving: Contacting Prod and Cons S2CS...")
        return random.random() < 0.5

    def release_resources(self):
        print("Releasing: Contacting Prod and Cons S2CS...")

    def commit_resources(self):
        print("Creating connection map and data connection credentials")

    def send_error_msg(self):
        print("ERROR...")

    def send_message(self, msg):
        print(msg)

    def __init__(self):
        states = ['idle', 'processing', 'streaming', 'releasing']

        transitions = [
            { 'trigger': 'UserReq', 'source': 'idle', 'dest': 'processing', 'conditions': 'reserve_resources'},
            { 'trigger': 'UserReq', 'source': 'idle', 'dest': None, 'before': 'send_error_msg'},
            { 'trigger': 'ReadyToStream', 'source': 'processing', 'dest': 'streaming', 'before': 'send_message'},
            { 'trigger': 'StopStreaming', 'source': 'streaming', 'dest': 'releasing', 'after': 'release_resources'},
            { 'trigger': 'Released', 'source': 'releasing', 'dest': 'idle'}
        ]

        Machine.__init__(self, states=states, transitions=transitions, initial='idle')

if __name__ == '__main__':
    s2uc = S2UC()
    s2uc.UserReq()
    if s2uc.state == 'processing':
        s2uc.ReadyToStream(msg="Ready to Stream")
        print(s2uc.state)
        sleep(random.randint(0,5))
        s2uc.StopStreaming()
        print(s2uc.state)
        s2uc.Released()
    print(s2uc.state)
