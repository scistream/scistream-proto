from src.s2ds.docker import Haproxy, Nginx, Stunnel
from src.s2ds.subproc import StunnelSubprocess, HaproxySubprocess
from typing import Union

class MockS2DS(S2DS):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start(self, num_conn, listener_ip):
        return {
            "s2ds_proc": [mock.MagicMock() for _ in range(num_conn)],
            "listeners": [f"{listener_ip}:500{i}" for i in range(num_conn)],
        }

    def release(self, entry):
        pass

    def update_listeners(self, listeners, s2ds_proc, uid):
        pass

def create_instance(instance_type):
    registry = {
        "haproxy": Haproxy,
        "nginx": Nginx,
        "stunnel": Stunnel,
        "stunnelsubprocess": lambda: StunnelSubprocess(logger),
        "haproxysubprocess": lambda: HaproxySubprocess(logger),
        "mock": lambda: MockS2DS(logger)
    }
    instance = registry.get(instance_type.lower())
    if not instance:
        print(f"Unsupported S2DS type: {instance_type}. Disabling S2DS")
        return MockS2DS(logger)
    return instance()
