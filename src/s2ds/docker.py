
from pathlib import Path
import docker
from jinja2 import Environment, FileSystemLoader
from src.s2ds.utils import get_config_path


class ProxyContainer:
    def __init__(self, service_plugin_type="docker"):
        self.service_plugin_type = service_plugin_type
        pass

    def release(self, entry):
        pass

    def start(self, num_conn, listener_ip):
        ##STOP hardcoding port 5001
        # self.local_ports = [5064 + i for i in range(num_conn)]
        self.local_ports = [5074, 5075, 5076, 6000, 6001]
        entry = {
            "s2ds_proc": [],
            "listeners": [f"{listener_ip}:{port}" for port in self.local_ports],
        }
        return entry

    def update_listeners(self, listeners, s2ds_proc, uid, role="PROD"):
        if self.service_plugin_type == "docker":
            docker_client = DockerPlugin()
        """
        if self.service_plugin_type == "janus":
            docker_client = JanusPlugin()
        if self.service_plugin_type == "dockersock":
            docker_client = DockerSockPlugin()
        """
        vars = {
            "local_ports": self.local_ports,
            "dest_array": listeners,
            "client": "yes" if role == "CONS" else "no",
        }
        # Load the Jinja2 environment and get the template
        env = Environment(loader=FileSystemLoader(f"{Path(__file__).parent}"))
        template = env.get_template(f"{self.cfg_filename}.j2")
        # Render the template to create the configuration file
        # renders file to a slightly different location

        config_path = get_config_path()

        with open(f"{config_path}/{self.cfg_filename}", "w") as f:
            f.write(template.render(vars))
        with open(f"{config_path}/{self.key_filename}", "w") as f:
            f.write("client1:" + uid.replace("-", ""))
        # Define the container configuration
        container_config = {
            "image": self.image_name,
            "name": self.container_name,
            "detach": True,
            "volumes": {
                f"{config_path}/{self.cfg_filename}": {
                    "bind": self.cfg_location,
                    "mode": "ro",
                },
                f"{config_path}/{self.key_filename}": {
                    "bind": self.key_location,
                    "mode": "ro",
                },
            },
            "network_mode": "host",
        }
        # Start the proxy container
        name = self.container_name

        docker_client.start(name, container_config)


class Haproxy(ProxyContainer):
    def __init__(self, service_plugin_type="docker"):
        self.service_plugin_type = service_plugin_type
        self.cfg_location = "/usr/local/etc/haproxy/haproxy.cfg"
        self.key_location = "/usr/local/etc/haproxy/haproxy.key"
        self.image_name = "haproxy:latest"
        self.container_name = "myhaproxy"
        self.cfg_filename = "haproxy.cfg"
        self.key_filename = "haproxy.cfg.j2"
        if self.service_plugin_type == "dockersock":
            self.cfg_filename = "/data/scistream-demo/configs/haproxy.cfg"
        pass


class Nginx(ProxyContainer):
    def __init__(self, service_plugin_type="docker"):
        self.service_plugin_type = service_plugin_type
        self.cfg_location = "/etc/nginx/nginx.conf"
        self.key_location = "/etc/nginx/nginx.key"
        self.image_name = "nginx:latest"
        self.container_name = "mynginx"
        self.cfg_filename = f"nginx.conf"
        self.key_filename = "nginx.conf.j2"
        if self.service_plugin_type == "dockersock":
            self.cfg_filename = "/data/scistream-demo/configs/nginx.conf"
        pass


class Stunnel(ProxyContainer):
    def __init__(self, service_plugin_type="docker"):
        self.service_plugin_type = service_plugin_type
        self.cfg_location = "/etc/stunnel/stunnel.conf"
        self.key_location = "/etc/stunnel/stunnel.key"
        self.image_name = "stunnel:latest"
        self.container_name = "mystunnel"
        self.cfg_filename = "stunnel.conf"
        self.key_filename = "stunnel.key"

        if self.service_plugin_type == "dockersock":
            self.cfg_filename = "/data/scistream-demo/configs/stunnel.conf"
            self.key_filename = "/data/scistream-demo/configs/stunnel.key"
        pass



class DockerPlugin:
    def __init__(self):
        self.client = docker.from_env()

    def start(self, name, container_config):
        try:
            container = self.client.containers.get(name)
            print(f"Container {name} already exists")
            container.restart()
        except docker.errors.NotFound:
            print(f"Creating container {name}")
            container = self.client.containers.run(**container_config)
        print(f"Started container with ID {container.id}")
