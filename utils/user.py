from transitions import Machine

class User(Machine):
    def send_user_req(self):
        print("User request sent!")

    def send_terminate(self):
        print("Terminating, goodbye")

    def __init__(self):
        states = ['started', 'waiting', 'accepted', 'rejected', 'streaming', 'stopped', 'terminated']

        transitions = [
            { 'trigger': 'UserReq', 'source': 'started', 'dest': 'waiting', 'before': 'send_user_req'},
            { 'trigger': 'ReqAccepted', 'source': 'waiting', 'dest': 'accepted'},
            { 'trigger': 'ERR', 'source': 'waiting', 'dest': 'rejected'},
            { 'trigger': 'ReadyToStream', 'source': 'accepted', 'dest': 'streaming'},
            { 'trigger': 'StopStreaming', 'source': 'streaming', 'dest': 'stopped'},
            { 'trigger': 'Terminate', 'source': ['stopped', 'rejected'], 'dest': 'terminated', 'before': 'send_terminate'}
        ]

        Machine.__init__(self, states=states, transitions=transitions, initial='started')

user = User()
print(user.state)
user.UserReq()
print(user.state)
user.ERR()
print(user.state)
user.Terminate()
print(user.state)
