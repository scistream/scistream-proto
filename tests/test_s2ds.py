import pytest
import socket
import threading
import time
import psutil
import subprocess
from pathlib import Path

from src.s2ds import StunnelSubprocess
import sys
import pytest
import time
import subprocess
import logging
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.s2ds import StunnelSubprocess
from src.s2ds import get_config_path  


@pytest.fixture
def mock_env_var(monkeypatch):
    """Fixture to set and unset environment variables"""
    def _set_env(var_name, var_value):
        monkeypatch.setenv(var_name, var_value)
    yield _set_env
    monkeypatch.delenv('HAPROXY_CONFIG_PATH', raising=False)

@pytest.fixture
def mock_home(monkeypatch, tmp_path):
    """Fixture to set a mock home directory"""
    monkeypatch.setenv('HOME', str(tmp_path))
    return tmp_path

def test_get_config_path_with_env_var(mock_env_var):
    #Environment variable overlaps other values
    mock_env_var('HAPROXY_CONFIG_PATH', '/custom/path')
    assert get_config_path() == '/custom/path'

def test_get_config_path_without_env_var(mock_home):
    # default path
    expected_path = os.path.join(mock_home, '.scistream')
    assert get_config_path() == expected_path
    assert os.path.exists(expected_path)

def test_get_config_path_creates_directory(mock_home):
    ## test not idempotent
    config_path = get_config_path()
    assert os.path.isdir(os.path.dirname(config_path))

def test_get_config_path_existing_directory(mock_home):
    ## test not idempotent
    os.makedirs(os.path.join(mock_home, '.scistream'), exist_ok=True)
    config_path = get_config_path()
    assert os.path.exists(config_path)

@pytest.fixture
def stunnel():
    return StunnelSubprocess()

@pytest.fixture(autouse=True)
def cleanup_processes():
    processes = []
    yield processes
    for proc in processes:
        proc.terminate()
        proc.wait()

@pytest.fixture
def stunnel_subprocess():
    return StunnelSubprocess()

@pytest.fixture
def mock_logger():
    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.INFO)
    return logger

def test_init(stunnel_subprocess):
    assert stunnel_subprocess.cfg_filename == 'stunnel.conf'
    assert isinstance(stunnel_subprocess.logger, logging.Logger)

def test_start(stunnel_subprocess, mock_logger):
    result = stunnel_subprocess.start(5, "127.0.0.1")
    assert len(result["listeners"]) == 5
    assert all(listener.startswith("127.0.0.1:") for listener in result["listeners"])
    assert result["s2ds_proc"] == []

def test_release_no_processes(stunnel_subprocess, mock_logger):
    entry = {"s2ds_proc": []}
    stunnel_subprocess.release(entry)
    # Check log output

def test_release_with_processes(stunnel_subprocess, mock_logger):
    # Start actual processes
    procs = [subprocess.Popen(["sleep", "10"]) for _ in range(3)]
    entry = {"s2ds_proc": procs}
    stunnel_subprocess.release(entry)
    
    ### PROCESS TERMINATION CAUSES A TYPE CHANGE IN THE ENTRY
    for proc in procs:
        assert isinstance(proc, int)

def test_generate_stunnel_config_content(stunnel_subprocess):
    uid = "test-uid"
    dest_array = ["192.168.1.1:443"]
    role = "CONS"
    stunnel_subprocess.start(5, "127.0.0.1") # maybe we should mock this
    config_path = stunnel_subprocess.generate_stunnel_config(uid, dest_array, role)
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    assert "client = yes" in content
    assert "192.168.1.1:443" in content
    assert str(Path(f"{uid}.key")) in content

@pytest.mark.parametrize("role,expected", [("CONS", "yes"), ("PROD", "no")])
def test_update_listeners(stunnel_subprocess, mock_logger, role, expected):
    listeners = ["127.0.0.1:8080"]
    s2ds_proc = []
    uid = "4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3"
    stunnel_subprocess.start(5, "127.0.0.1")
    stunnel_subprocess.update_listeners(listeners, s2ds_proc, uid, role)
    assert len(s2ds_proc) == 1
    if s2ds_proc[0].poll() is None :  # Process should be running
    # Clean up
        s2ds_proc[0].terminate()
        ## Output not working
        #output = ''.join(s2ds_proc[0].stderr)
        #print(output)

def test_full_cycle(stunnel_subprocess):
    # Start
    entry = stunnel_subprocess.start(5, "127.0.0.1")
    assert len(entry["listeners"]) == 5
    
    # Update listeners
    stunnel_subprocess.update_listeners(entry["listeners"], entry["s2ds_proc"], "test-uid", "CONS")
    assert len(entry["s2ds_proc"]) == 1
    assert entry["s2ds_proc"][0].poll() is None  # Process should be running
    
    # Release
    stunnel_subprocess.release(entry)
    time.sleep(0.1)  # Give some time for the process to terminate
    assert entry["s2ds_proc"][0].poll() is not None  # Process should have terminated



@pytest.fixture
def stunnel_subprocess():
    return StunnelSubprocess()

@pytest.fixture
def mock_logger():
    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.INFO)
    return logger

def test_start_multiple_subprocesses(stunnel_subprocess):
    result1 = stunnel_subprocess.start(3, "127.0.0.1")
    result2 = stunnel_subprocess.start(2, "127.0.0.1")
    
    assert len(result1["listeners"]) == 3
    assert len(result2["listeners"]) == 2
    assert all(listener.startswith("127.0.0.1:") for listener in result1["listeners"] + result2["listeners"])
    assert len(set(result1["listeners"]).intersection(set(result2["listeners"]))) == 0  # No overlapping ports

    stunnel_subprocess.release(result1)
    stunnel_subprocess.release(result2)

def test_start_until_system_limit(stunnel_subprocess, mock_logger):
    results = []
    try:
        while True:
            result = stunnel_subprocess.start(1, "127.0.0.1")
            results.append(result)
    except Exception as e:
        mock_logger.info(f"System limit reached or error occurred: {e}")
    
    assert len(results) > 0
    mock_logger.info(f"Successfully started {len(results)} subprocesses before hitting limit")

    for result in results:
        stunnel_subprocess.release(result)

def test_port_conflict(stunnel_subprocess):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    occupied_port = sock.getsockname()[1]

    with pytest.raises(Exception):  # Replace with specific exception if applicable
        stunnel_subprocess.start(1, "127.0.0.1", start_port=occupied_port)

    sock.close()

def test_rapid_start_release_cycles(stunnel_subprocess):
    for _ in range(50):
        result = stunnel_subprocess.start(1, "127.0.0.1")
        assert len(result["listeners"]) == 1
        stunnel_subprocess.release(result)

def test_concurrent_operations(stunnel_subprocess):
    def start_and_release():
        result = stunnel_subprocess.start(1, "127.0.0.1")
        stunnel_subprocess.release(result)

    threads = [threading.Thread(target=start_and_release) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert all(not thread.is_alive() for thread in threads)

def test_long_running_subprocess(stunnel_subprocess):
    result = stunnel_subprocess.start(1, "127.0.0.1")
    
    time.sleep(10)  # Run for 10 seconds

    assert result["s2ds_proc"][0].poll() is None  # Process should be running

    stunnel_subprocess.update_listeners(result["listeners"], result["s2ds_proc"], "test-uid", "CONS")

    stunnel_subprocess.release(result)

def test_error_recovery(stunnel_subprocess, monkeypatch):
    def mock_popen(*args, **kwargs):
        raise OSError("Simulated error")

    monkeypatch.setattr(subprocess, 'Popen', mock_popen)
    
    with pytest.raises(OSError):
        stunnel_subprocess.start(1, "127.0.0.1")

    monkeypatch.undo()
    result = stunnel_subprocess.start(1, "127.0.0.1")
    
    assert len(result["listeners"]) == 1
    stunnel_subprocess.release(result)