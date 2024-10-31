import logging
import subprocess
from pathlib import Path
from src.s2ds.utils import get_config_path
from jinja2 import Environment, FileSystemLoader

class AbstractSubprocess():
    def __init__(self, logger=None):
        self.logger = logger if logger else logging.getLogger(__name__)
        # These need to be defined by child classes
        self.cfg_filename = None
        self.command = None
        self.local_ports = None
    
    def start(self, num_conn, listener_ip, ports):
        self.logger.info(f"Reserving {self.command} ports: {ports}")
        self.local_ports = ports
        entry = {
            "s2ds_proc": [],
            "listeners": [f"{listener_ip}:{port}" for port in ports[:num_conn]],
        }
        return entry
    
    def release(self, entry):
        if not entry["s2ds_proc"]:
            self.logger.info(f"No {self.command} subprocesses to terminate")
            return
        
        error_occurred = False
        for i, rem_proc in enumerate(entry["s2ds_proc"]):
            try:
                rem_proc.terminate()
                entry["s2ds_proc"][i] = rem_proc.pid
            except Exception as e:
                self.logger.error(f"Error terminating process {rem_proc.pid}: {e}")
                error_occurred = True
        
        if not error_occurred:
            self.logger.info(f"Terminated {self.command} subprocess(es)")
    
    def update_listeners(self, listeners, s2ds_proc, uid, role):
        self.logger.info(listeners)
        config_path = self.generate_config(uid, listeners, role)
        self.command.append(config_path)
        new_proc = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        s2ds_proc.append(new_proc)
        self.logger.info(f"Updating {self.command} destination (no action required)")
    
    def generate_config(self, uid, dest_array, role):
        env = Environment(loader=FileSystemLoader(Path(__file__).parent))
        template = env.get_template(f"{self.cfg_filename}.j2")
        key_filename = Path(get_config_path()) / f"{uid}.key"
        pid_filename = Path(get_config_path()) / f"{uid}.pid"
        
        config_content = template.render(
            dest_array=dest_array,
            local_ports=self.local_ports,
            client="yes" if role == "CONS" else "no",
            key_filename=str(key_filename),
            pid_filename=str(pid_filename),
        )
        config_path = Path(get_config_path()) / f"{uid}.conf"
        config_path.write_text(config_content)
        self.write_key_file(key_filename, uid)
        return str(config_path)

    def write_key_file(self, key_filename, uid):
        key_filename.write_text("client1:" + uid.replace("-", ""))

class StunnelSubprocess(AbstractSubprocess):
    def __init__(self, logger=None):
        super().__init__(logger)
        self.cfg_filename = "stunnel.conf"
        self.command = ["stunnel"]

class HaproxySubprocess(AbstractSubprocess):
    def __init__(self, logger=None):
        super().__init__(logger)
        self.cfg_filename = "haproxy.cfg"
        self.command = ["haproxy", "-f"]