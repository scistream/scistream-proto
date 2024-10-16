import os
import logging
import subprocess
from pathlib import Path

class S2DSException(Exception):
    pass
    
    
def get_config_path():
    # Check if the environment variable for HAProxy config path is set
    config_path = os.environ.get("HAPROXY_CONFIG_PATH")

    if config_path:
        # If the environment variable is set, use its value
        return config_path
    else:
        # If the environment variable is not set, use the default path
        default_path = os.path.expanduser("~/.scistream")

        # Create the directory if it doesn't exist
        os.makedirs(default_path, exist_ok=True)

        # Create the file if it doesn't exist
        if not os.path.exists(default_path):
            open(default_path, "a").close()

        return default_path


class S2DS:
    ## TODO Cleanup
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def start(self, num_conn, listener_ip):
        self.logger.info(f"Starting {num_conn} S2DS subprocess(es)...")
        s2ds_path = (
            Path(__file__).resolve().parent.parent / "scistream" / "S2DS" / "S2DS.out"
        )
        entry = {"s2ds_proc": [], "listeners": []}
        try:
            for _ in range(num_conn):
                new_proc = subprocess.Popen(
                    [s2ds_path], stdout=subprocess.PIPE, stdin=subprocess.PIPE
                )
                new_listener_port = (
                    new_proc.stdout.readline().decode("utf-8").split("\n")[0]
                )
                if (
                    not new_listener_port.isdigit()
                    or int(new_listener_port) < 0
                    or int(new_listener_port) > 65535
                ):
                    raise S2DSException(
                        f"S2DS subprocess returned invalid listener port '{new_listener_port}'"
                    )
                new_listener = listener_ip + ":" + new_listener_port
                entry["s2ds_proc"].append(new_proc)
                entry["listeners"].append(new_listener)
        except Exception as e:
            self.logger.error(f"Error starting S2DS subprocess(es): {e}")
            raise S2DSException(f"Error starting S2DS subprocess(es): {e}") from e
        return entry

    def release(self, entry):
        ## potential for race condition here
        ## PIDs are operating system dependent vs subprocess object
        ## how do we ensure I/O streams are well taken care of
        ## logging.
        if entry["s2ds_proc"] != []:
            for i, rem_proc in enumerate(entry["s2ds_proc"]):
                rem_proc.terminate()  # TODO: Make sure s2ds buffer handles this signal gracefully
                entry["s2ds_proc"][
                    i
                ] = rem_proc.pid  # Print out PID rather than Popen object
            self.logger.info(
                f"Terminated {len(entry['s2ds_proc'])} S2DS subprocess(es)"
            )

    def update_listeners(self, listeners, s2ds_proc, uid, role):
        # Send remote port information to S2DS subprocesses in format "remote_ip:remote_port\n"
        for i in range(len(listeners)):
            curr_proc = s2ds_proc[i]
            curr_remote_conn = listeners[i] + "\n"
            if curr_proc.poll() is not None:
                raise S2DSException(
                    f"S2DS subprocess with PID '{curr_proc.pid}' unexpectedly quit"
                )
            curr_proc.stdin.write(curr_remote_conn.encode())
            curr_proc.stdin.flush()
            self.logger.info(
                f"S2DS subprocess establishing connection with {curr_remote_conn.strip()}..."
            )
