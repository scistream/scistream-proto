import os
import logging
import subprocess
from pathlib import Path
import requests
import json
import time
import urllib3

class S2DSException(Exception):
    pass

##Instance Names allowed:
# Haproxy
# Nginx
# Stunnel
def create_instance(class_name):
    try:
        instance = eval(f"{class_name}()")
        return instance
    except NameError:
         print(f"Class {class_name} is not defined.")
    return create_instance(type)

def get_haproxy_config_path():
    # Check if the environment variable for HAProxy config path is set
    config_path = os.environ.get('HAPROXY_CONFIG_PATH')

    if config_path:
        # If the environment variable is set, use its value
        return config_path
    else:
        # If the environment variable is not set, use the default path
        default_path = os.path.expanduser('~/.scistream')

        # Create the directory if it doesn't exist
        os.makedirs(default_path, exist_ok=True)

        # Create the file if it doesn't exist
        if not os.path.exists(default_path):
            open(default_path, 'a').close()

        return default_path

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

    def update_listeners(self, listeners, s2ds_proc, uid, role):
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

class ProxyContainer():
    def __init__(self, service_plugin_type="docker"):
        self.service_plugin_type = service_plugin_type
        pass

    def release(self, entry):
        pass

    def start(self, num_conn, listener_ip):
        ##STOP hardcoding port 5001
        #self.local_ports = [5064 + i for i in range(num_conn)]
        self.local_ports = [5074, 5075, 5076, 6000, 6001]
        entry={"s2ds_proc":[], "listeners":[f"{listener_ip}:{port}" for port in self.local_ports]}
        return entry

    def update_listeners(self, listeners, s2ds_proc, uid, role = "PROD"):
        if self.service_plugin_type == "docker":
           docker_client = DockerPlugin()
        if self.service_plugin_type == "janus":
           docker_client = JanusPlugin()
        if self.service_plugin_type == "dockersock":
           docker_client = DockerSockPlugin()

        vars = {
            'local_ports': self.local_ports,
            'dest_array': listeners,
            'client': "yes" if role == "CONS" else "no"
        }
        # Load the Jinja2 environment and get the template
        env = Environment(loader=FileSystemLoader(f'{Path(__file__).parent}'))
        template = env.get_template(f'{self.cfg_filename}.j2')
        # Render the template to create the configuration file
        #renders file to a slightly different location

        config_path = get_haproxy_config_path()

        with open(f'{config_path}/{self.cfg_filename}', 'w') as f:
            f.write(template.render(vars))
        with open(f'{config_path}/{self.key_filename}', 'w') as f:
            f.write("client1:"+uid.replace("-", ""))
        # Define the container configuration
        container_config = {
            'image': self.image_name ,
            'name': self.container_name,
            'detach': True,
            'volumes': {
                        f"{config_path}/{self.cfg_filename}": {'bind': self.cfg_location, 'mode': 'ro'},
                        f"{config_path}/{self.key_filename}": {'bind': self.key_location, 'mode': 'ro'}
                        },
            'network_mode': 'host'
        }
        # Start the proxy container
        name = self.container_name
        
        docker_client.start(name, container_config)

 
class Haproxy(ProxyContainer):
    def __init__(self, service_plugin_type="docker"):
        self.service_plugin_type = service_plugin_type
        self.cfg_location = '/usr/local/etc/haproxy/haproxy.cfg'
        self.key_location = '/usr/local/etc/haproxy/haproxy.key'
        self.image_name = 'haproxy:latest'
        self.container_name = "myhaproxy"
        self.cfg_filename = 'haproxy.cfg'
        self.key_filename = 'haproxy.cfg.j2'
        if self.service_plugin_type == "dockersock":
           self.cfg_filename = "/data/scistream-demo/configs/haproxy.cfg"
        pass

class Nginx(ProxyContainer):
    def __init__(self, service_plugin_type="docker"):
        self.service_plugin_type = service_plugin_type
        self.cfg_location = '/etc/nginx/nginx.conf'
        self.key_location = '/etc/nginx/nginx.key'
        self.image_name = 'nginx:latest'
        self.container_name = "mynginx"
        self.cfg_filename = f'nginx.conf'
        self.key_filename = 'nginx.conf.j2'
        if self.service_plugin_type == "dockersock":
           self.cfg_filename = "/data/scistream-demo/configs/nginx.conf"
        pass

class Stunnel(ProxyContainer):
    def __init__(self, service_plugin_type="docker"):
        self.service_plugin_type = service_plugin_type
        self.cfg_location = '/etc/stunnel/stunnel.conf'
        self.key_location = '/etc/stunnel/stunnel.key'
        self.image_name = 'stunnel:latest'
        self.container_name = "mystunnel"
        self.cfg_filename = 'stunnel.conf'
        self.key_filename = 'stunnel.key'
        
        if self.service_plugin_type == "dockersock":
            self.cfg_filename = "/data/scistream-demo/configs/stunnel.conf"
            self.key_filename = "/data/scistream-demo/configs/stunnel.key"
        pass

class Janus(Haproxy):
    def __init__(self):
        self.service_plugin_type = "janus"

class DockerSock(Haproxy):
    def __init__(self):
        self.service_plugin_type = "dockersock"

class DockerPlugin():
    def __init__(self):
        self.client = docker.from_env()

    def start(self, name, container_config):
        try:
            container = self.client.containers.get(name)
            print(f'Container {name} already exists')
            container.restart()
        except docker.errors.NotFound:
            print(f'Creating container {name}')
            container = self.client.containers.run(**container_config)
        print(f'Started container with ID {container.id}')

class DockerSockPlugin(DockerPlugin):
    def __init__(self):
        self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')

class JanusPlugin():
    def __init__(self):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.auth = ('admin', 'admin')# update this

    def start(name, container_config):
        ## check if a container exists
        active_session = requests.put(url='https://nersc-srv-1.testbed100.es.net:5000/api/janus/controller/active', auth=self.auth, verify=False)
        if len(active_session.json()) == 0:
            ## create container
            response = requests.post(url="https://nersc-srv-1.testbed100.es.net:5000/api/janus/controller/create", auth = self.auth, json={"errors":[],"instances":["nersc-dtnaas-1"],"image":"haproxy:latest","profile":"scistream-demo","arguments":"","kwargs":{"USER_NAME":"","PUBLIC_KEY":""},"remove_container":"None"}, verify=False)
            assert response.status_code == 200
            session_id = list(json.loads(response.text).keys())[0]
            print("JANUS CONTAINER DOESNT EXIST")
        else:
            session_id = active_session.json()[0]['id']
            print("JANUS CONTAINER EXIST")
        print(f"SESSION_ID = {session_id}")
        ## Container exists, now update config stop and start
        cfg= Path(__file__).parent / "haproxy.cfg"
        dest_path = Path("/data/scistream-demo/configs/haproxy.cfg")
        os.system(f'cp {cfg} {dest_path}')
        ## This assumes we are running this code in the same location as the docker platform
        stop_response = requests.put(url=f'https://nersc-srv-1.testbed100.es.net:5000/api/janus/controller/stop/{session_id}', auth=self.auth, verify=False)
        start_response = requests.put(url=f'https://nersc-srv-1.testbed100.es.net:5000/api/janus/controller/start/{session_id}', auth=self.auth, verify=False)
