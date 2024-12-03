from src.s2ds.docker import Haproxy, Nginx, Stunnel
from src.s2ds.subproc import StunnelSubprocess, HaproxySubprocess
from typing import Union

def create_instance(instance_type: str, logger=None) -> Union[Haproxy, Nginx, Stunnel, StunnelSubprocess, None]:
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
        return None