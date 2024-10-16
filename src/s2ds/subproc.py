import logging
import subprocess
from pathlib import Path
from src.s2ds.utils import get_config_path
from jinja2 import Environment, FileSystemLoader

class StunnelSubprocess:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cfg_filename = "stunnel.conf"

    def start(self, num_conn, listener_ip):
        ## better terminology is reserve instead of start
        self.logger.info(f"Reserving Stunnel ports...")
        # Hardcoding local ports for now
        self.local_ports = [5074, 5075, 5076, 6000, 6001]
        entry = {
            "s2ds_proc": [],
            "listeners": [f"{listener_ip}:{port}" for port in self.local_ports],
        }
        return entry

    def release(self, entry):
        if not entry["s2ds_proc"]:
            self.logger.info("No Stunnel subprocesses to terminate")
            return
        error_occurred = False

        for i, rem_proc in enumerate(entry["s2ds_proc"]):
            try:
                rem_proc.terminate()  # tightly coupled with S2CS
                entry["s2ds_proc"][i] = rem_proc.pid  # type change
            except Exception as e:
                self.logger.error(f"Error terminating process {rem_proc.pid}: {e}")
                error_occurred = True
        if not error_occurred:
            self.logger.info(f"Terminated Stunnel subprocess(es)")

    def update_listeners(self, listeners, s2ds_proc, uid, role):
        ## actively trying to update mutable object s2ds_proc
        # better terminology is program destination.
        config_path = self.generate_stunnel_config(uid, listeners, role)
        new_proc = subprocess.Popen(
            ["stunnel", config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        s2ds_proc.append(new_proc)
        self.logger.info("Updating Stunnel destination (no action required)")

    def generate_stunnel_config(self, uid, dest_array, role):
        ## uid is NOT confidential as of now.
        ## However uid is used as PSK for stunnel
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
        # Write the configuration to a file and key to a file
        config_path = Path(get_config_path()) / f"{uid}.conf"
        config_path.write_text(config_content)
        ## reference to key location hardcoded in j2 template
        ## key content must follow some openssl rules
        key_filename.write_text("client1:" + uid.replace("-", ""))
        return str(config_path)