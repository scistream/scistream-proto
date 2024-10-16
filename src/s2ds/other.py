

class Janus(Haproxy):
    def __init__(self):
        self.service_plugin_type = "janus"


class DockerSock(Haproxy):
    def __init__(self):
        self.service_plugin_type = "dockersock"


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


class DockerSockPlugin(DockerPlugin):
    def __init__(self):
        self.client = docker.DockerClient(base_url="unix://var/run/docker.sock")


class JanusPlugin:
    def __init__(self):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.auth = ("admin", "admin")  # update this

    def start(name, container_config):
        ## check if a container exists
        active_session = requests.put(
            url="https://nersc-srv-1.testbed100.es.net:5000/api/janus/controller/active",
            auth=self.auth,
            verify=False,
        )
        if len(active_session.json()) == 0:
            ## create container
            response = requests.post(
                url="https://nersc-srv-1.testbed100.es.net:5000/api/janus/controller/create",
                auth=self.auth,
                json={
                    "errors": [],
                    "instances": ["nersc-dtnaas-1"],
                    "image": "haproxy:latest",
                    "profile": "scistream-demo",
                    "arguments": "",
                    "kwargs": {"USER_NAME": "", "PUBLIC_KEY": ""},
                    "remove_container": "None",
                },
                verify=False,
            )
            assert response.status_code == 200
            session_id = list(json.loads(response.text).keys())[0]
            print("JANUS CONTAINER DOESNT EXIST")
        else:
            session_id = active_session.json()[0]["id"]
            print("JANUS CONTAINER EXIST")
        print(f"SESSION_ID = {session_id}")
        ## Container exists, now update config stop and start
        cfg = Path(__file__).parent / "haproxy.cfg"
        dest_path = Path("/data/scistream-demo/configs/haproxy.cfg")
        os.system(f"cp {cfg} {dest_path}")
        ## This assumes we are running this code in the same location as the docker platform
        stop_response = requests.put(
            url=f"https://nersc-srv-1.testbed100.es.net:5000/api/janus/controller/stop/{session_id}",
            auth=self.auth,
            verify=False,
        )
        start_response = requests.put(
            url=f"https://nersc-srv-1.testbed100.es.net:5000/api/janus/controller/start/{session_id}",
            auth=self.auth,
            verify=False,
        )



