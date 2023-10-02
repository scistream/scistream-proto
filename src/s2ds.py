import os
import logging
import subprocess
from pathlib import Path

class S2DSException(Exception):
    pass

def create_instance(class_name):
    try:
        instance = eval(f"{class_name}()")
        return instance
    except NameError:
         print(f"Class {class_name} is not defined.")
    return create_instance(type)

class S2DS():
    ## TODO Cleanup
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def start(self, num_conn, listener_ip):
        self.logger.info(f"Starting {num_conn} S2DS subprocess(es)...")
        s2ds_path =  Path(__file__).resolve().parent.parent / "scistream" / "S2DS" / "S2DS.out"
        entry={"s2ds_proc":[], "listeners":[]}
        try:
            for _ in range(num_conn):
                new_proc = subprocess.Popen([s2ds_path], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                new_listener_port = new_proc.stdout.readline().decode("utf-8").split("\n")[0]
                if not new_listener_port.isdigit() or int(new_listener_port) < 0 or int(new_listener_port) > 65535:
                    raise S2DSException(f"S2DS subprocess returned invalid listener port '{new_listener_port}'")
                new_listener = listener_ip + ":" + new_listener_port
                entry["s2ds_proc"].append(new_proc)
                entry["listeners"].append(new_listener)
        except Exception as e:
            self.logger.error(f"Error starting S2DS subprocess(es): {e}")
            raise S2DSException(f"Error starting S2DS subprocess(es): {e}") from e
        return entry

    def release(self, entry):
        if entry["s2ds_proc"] != []:
            for i, rem_proc in enumerate(entry["s2ds_proc"]):
                rem_proc.terminate() # TODO: Make sure s2ds buffer handles this signal gracefully
                entry["s2ds_proc"][i] = rem_proc.pid # Print out PID rather than Popen object
            self.logger.info(f"Terminated {len(entry['s2ds_proc'])} S2DS subprocess(es)")

    def update_listeners(self, listeners, s2ds_proc):
        # Send remote port information to S2DS subprocesses in format "remote_ip:remote_port\n"
        for i in range(len(listeners)):
            curr_proc = s2ds_proc[i]
            curr_remote_conn = listeners[i] + "\n"
            if curr_proc.poll() is not None:
                raise S2CSException(f"S2DS subprocess with PID '{curr_proc.pid}' unexpectedly quit")
            curr_proc.stdin.write(curr_remote_conn.encode())
            curr_proc.stdin.flush()
            self.logger.info(f"S2DS subprocess establishing connection with {curr_remote_conn.strip()}...")

import docker
from jinja2 import Environment, FileSystemLoader

class Haproxy():
    def __init__(self):
        pass

    def release(self, entry):
        pass

    def start(self, num_conn, listener_ip):
        ##STOP hardcoding port 5001
        self.local_port= "5001"
        entry={"s2ds_proc":[], "listeners":[f"{listener_ip}:{self.local_port}"]}
        return entry

    def update_listeners(self, listeners, s2ds_proc):
        remote_host, remote_port = listeners[0].split(":")
        vars = {
            'local_port': self.local_port,
            'remote_host': remote_host,
            'remote_port': remote_port,
        }
        # Load the Jinja2 environment and get the template
        env = Environment(loader=FileSystemLoader(f'{Path(__file__).parent}'))
        template = env.get_template(f'haproxy.cfg.j2')
        # Render the template to create the HAProxy configuration file
        #renders file to a slightly different location
        with open(f'{Path(__file__).parent}/haproxy.cfg', 'w') as f:
            f.write(template.render(vars))

        # Connect to Docker
        client = docker.from_env()

        # Define the HAProxy container configuration
        container_config = {
            'image': 'haproxy:latest',
            'name': 'myhaproxy',
            'detach': True,
            'volumes': {f'{Path(__file__).parent}/haproxy.cfg': {'bind': '/usr/local/etc/haproxy/haproxy.cfg', 'mode': 'ro'}},
            'network_mode': 'host'
        }
        # Start the HAProxy container
        name= "myhaproxy"
        try:
            container = client.containers.get(name)
            print(f'Container {name} already exists')
            container.stop()
            container.remove()
            print(f'Creating container {name}')
            container = client.containers.run(**container_config)

        except docker.errors.NotFound:
            print(f'Creating container {name}')
            container = client.containers.run(**container_config)

        print(f'Started HAProxy container with ID {container.id}')

class Nginx():
    def __init__(self):
        pass

    def release(self, entry):
        pass

    def start(self, num_conn, listener_ip):
        entry={"s2ds_proc":[], "listeners":["127.0.0.1:5002"]}
        return entry

    def update_listeners(self, listeners, s2ds_proc):
        remote_host, remote_port = listeners[0].split(":")
        local_port=5002
        vars = {
            'local_port': local_port,
            'remote_host': remote_host,
            'remote_port': remote_port,
        }
        # Load the Jinja2 environment and get the template
        env = Environment(loader=FileSystemLoader(f'{Path(__file__).parent}'))
        template = env.get_template(f'nginx.conf.j2')
        # Render the template to create the NGINX configuration file
        with open('nginx.conf', 'w') as f:
            f.write(template.render(vars))

        # Connect to Docker
        client = docker.from_env()

        # Define the NGINX container configuration
        container_config = {
            'image': 'nginx:latest',
            'name': 'mynginx',
            'detach': True,
            'ports': {f'{local_port}/tcp':local_port},
            'volumes': {f'{Path(__file__).parent}/nginx.conf': {'bind': '/etc/nginx/nginx.conf', 'mode': 'ro'}},
            'network': 'mynetwork',
        }
        # Start the NGINX container
        name= "mynginx"
        try:
            container = client.containers.get(name)
            print(f'Container {name} already exists')
        except docker.errors.NotFound:
            print(f'Creating container {name}')
            container = client.containers.run(**container_config)

        print(f'Started NGINX container with ID {container.id}')
