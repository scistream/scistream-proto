from src.s2ds.docker import Haproxy, Nginx, Stunnel
from src.s2ds.subproc import StunnelSubprocess, HaproxySubprocess
from unittest import mock

class MockS2DS():
    def __init__(self, *args, **kwargs):
        pass

    def start(self, num_conn, listener_ip):
        return {
            "s2ds_proc": [mock.MagicMock() for _ in range(num_conn)],
            "listeners": [f"{listener_ip}:500{i}" for i in range(num_conn)],
        }

    def release(self, entry):
        pass

    def update_listeners(self, listeners, s2ds_proc, uid, role):
        pass

def create_instance(instance_type, logger=None):
    if instance_type == "Haproxy":
        return Haproxy()
    elif instance_type == "Nginx":
        return Nginx()
    elif instance_type == "Stunnel":
        return Stunnel()
    elif instance_type == "StunnelSubprocess":
        return StunnelSubprocess(logger)
    elif instance_type == "HaproxySubprocess":
        return HaproxySubprocess(logger)
    else:
        print(f"Unsupported instance type: {instance_type}")
        return MockS2DS()

