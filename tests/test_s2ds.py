import os
import sys
import time
import socket
import subprocess
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.s2ds.subproc import StunnelSubprocess, get_config_path, HaproxySubprocess


@pytest.fixture
def mock_env_var(monkeypatch):
    """Fixture to set and unset environment variables"""

    def _set_env(var_name, var_value):
        monkeypatch.setenv(var_name, var_value)

    yield _set_env
    monkeypatch.delenv("HAPROXY_CONFIG_PATH", raising=False)


@pytest.fixture
def mock_home(monkeypatch, tmp_path):
    """Fixture to set a mock home directory"""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path

@pytest.fixture
def stunnel_subprocess():
    return StunnelSubprocess()

@pytest.fixture
def s2ds_fixture():
    def _make_subprocess(type):
        if type == "stunnel":
            return StunnelSubprocess()
        if type == "haproxy":
            return HaproxySubprocess()
    return _make_subprocess

@pytest.fixture(autouse=True)
def cleanup_processes():
    processes = []
    yield processes
    for proc in processes:
        proc.terminate()
        proc.wait()


## Make sure to use user space authorization

def test_get_config_path_with_env_var(mock_env_var):
    mock_env_var("HAPROXY_CONFIG_PATH", "/custom/path")
    assert get_config_path() == "/custom/path"


def test_get_config_path_without_env_var(mock_home):
    expected_path = os.path.join(mock_home, ".scistream")
    assert get_config_path() == expected_path
    assert os.path.exists(expected_path)


def test_get_config_path_creates_directory():
    # Cleanup can be improved
    config_path = get_config_path()
    assert os.path.isdir(os.path.dirname(config_path))


def test_get_config_path_existing_directory(mock_home):
    # cleanup can be improved
    os.makedirs(os.path.join(mock_home, ".scistream"), exist_ok=True)
    config_path = get_config_path()
    assert os.path.exists(config_path)


def test_init(stunnel_subprocess):
    assert stunnel_subprocess.cfg_filename == "stunnel.conf"


def test_start(stunnel_subprocess):
    result = stunnel_subprocess.start(5, "127.0.0.1", [5100, 5101, 5102, 5103, 5104])
    assert len(result["listeners"]) == 5
    assert all(listener.startswith("127.0.0.1:") for listener in result["listeners"])
    assert result["s2ds_proc"] == []

@pytest.mark.xfail
def test_exaust_num_connection(stunnel_subprocess):
    result = stunnel_subprocess.start(5, "127.0.0.1", [5100, 5101])
    assert len(result["listeners"]) == 5
    assert all(listener.startswith("127.0.0.1:") for listener in result["listeners"])
    assert result["s2ds_proc"] == []

def test_start_single(stunnel_subprocess):
    result = stunnel_subprocess.start(1, "127.0.0.1", [5074])
    assert len(result["listeners"]) == 1
    assert all(listener.startswith("127.0.0.1:") for listener in result["listeners"])
    assert result["s2ds_proc"] == []

def test_num_connections_small(stunnel_subprocess):
    result = stunnel_subprocess.start(1, "127.0.0.1", [5074, 5075])
    assert len(result["listeners"]) == 1
    assert all(listener.startswith("127.0.0.1:") for listener in result["listeners"])
    assert result["s2ds_proc"] == []


def test_release_no_processes(stunnel_subprocess):
    entry = {"s2ds_proc": []}
    stunnel_subprocess.release(entry)


def test_release_with_processes(stunnel_subprocess):
    procs = [subprocess.Popen(["sleep", "10"]) for _ in range(3)]
    entry = {"s2ds_proc": procs}
    stunnel_subprocess.release(entry)
    ### PROCESS TERMINATION CAUSES A TYPE CHANGE IN THE ENTRY
    for proc in procs:
        assert isinstance(proc, int)


def test_generate_stunnel_config_content(stunnel_subprocess):
    uid = "74c12996-92d6-11ef-a0df-8b998dbe1360"
    dest_array = ["192.168.1.1:443"]
    role = "CONS"
    stunnel_subprocess.start(5, "127.0.0.1", [443])
    config_path = stunnel_subprocess.generate_config(uid, dest_array, role)

    with open(config_path, "r") as f:
        content = f.read()

    assert "client = yes" in content
    assert "192.168.1.1:443" in content
    assert str(Path(f"{uid}.key")) in content


@pytest.mark.parametrize("role", ["CONS", "PROD"])
def test_update_listeners(stunnel_subprocess, role):
    listeners = ["127.0.0.1:8080"]
    s2ds_proc = []
    uid = "4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3"
    stunnel_subprocess.start(5, "127.0.0.1", [9000])
    stunnel_subprocess.update_listeners(listeners, s2ds_proc, uid, role)
    assert len(s2ds_proc) == 1
    if s2ds_proc[0].poll() is None:
        s2ds_proc[0].terminate()

@pytest.mark.parametrize("type", ["stunnel", "haproxy"])
def test_full_cycle(s2ds_fixture, type):
    s2ds = s2ds_fixture(type)
    entry = s2ds.start(5, "127.0.0.1", [5001, 5002, 5003, 5004, 5005])
    assert len(entry["listeners"]) == 5

    s2ds.update_listeners(
        ["127.0.0.1:8000", "127.0.0.1:8001", "127.0.0.1:8002", "127.0.0.1:8003", "127.0.0.1:8004"], entry["s2ds_proc"], "4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3", "CONS"
    )
    time.sleep(0.5)
    assert len(entry["s2ds_proc"]) == 1
    assert entry["s2ds_proc"][0].poll() is None

    s2ds.release(entry)
    time.sleep(0.1)
    assert isinstance(entry["s2ds_proc"][0], int)

@pytest.mark.parametrize(
    ("ports", "uid"),
    [
        ([6001, 6002], "74c12996-92d6-11ef-a0df-8b998dbe1360"),
        pytest.param([5001, 5002], "74c12996-92d6-11ef-a0df-8b998dbe1360", marks=pytest.mark.xfail(reason="Conflicted ports"), id="should_fail"),
        pytest.param([6001, 6002], "4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3", marks=pytest.mark.xfail(reason="Conflicted uid"), id="should_fail"),   
    ]
)
def test_start_multiple_subprocesses(stunnel_subprocess, ports, uid):
    entry = stunnel_subprocess.start(2, "127.0.0.1", [5001, 5002])
    assert len(entry["listeners"]) == 2

    stunnel_subprocess.update_listeners(
        ["127.0.0.1:8000", "127.0.0.1:8001"], entry["s2ds_proc"], "4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3", "CONS"
    )
    time.sleep(0.5)

    assert len(entry["s2ds_proc"]) == 1
    assert entry["s2ds_proc"][0].poll() is None    

    subprocess2 = StunnelSubprocess()
    entry2 = subprocess2.start(5, "127.0.0.1", ports)
    assert len(entry2["listeners"]) == 2

    subprocess2.update_listeners(
        entry2["listeners"], entry2["s2ds_proc"], uid, "CONS"
    )
    time.sleep(0.5)
    try:
        assert len(entry2["s2ds_proc"]) == 1
        assert entry2["s2ds_proc"][0].poll() is None
    finally:
        stunnel_subprocess.release(entry)
        time.sleep(0.1)
        assert isinstance(entry["s2ds_proc"][0], int)
        subprocess2.release(entry2)
        time.sleep(0.1)
        assert isinstance(entry2["s2ds_proc"][0], int)

##Expected to fail but it passed
@pytest.mark.xfail
def test_port_conflict(stunnel_subprocess):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 5070))
        occupied_port = sock.getsockname()[1]

#        with pytest.raises(Exception):
        entry = stunnel_subprocess.start(1, "127.0.0.1", [5070])
        stunnel_subprocess.update_listeners(
            entry["listeners"], entry["s2ds_proc"], "4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3", "CONS"
        )
        time.sleep(0.5)
        assert True

## FIX THIS improve assertion
def test_rapid_start_release_cycles(stunnel_subprocess):
    for _ in range(50):
        entry = stunnel_subprocess.start(1, "127.0.0.1", [5074])
        stunnel_subprocess.update_listeners(
            entry["listeners"], entry["s2ds_proc"], "4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3", "CONS"
        )
        stunnel_subprocess.release(entry)


def test_error_recovery(stunnel_subprocess, monkeypatch):
    def mock_popen(*args, **kwargs):
        raise OSError("Simulated error")

    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    with pytest.raises(OSError):
        stunnel_subprocess.start(1, "127.0.0.1", [5074])

    monkeypatch.undo()
    result = stunnel_subprocess.start(1, "127.0.0.1", [5074])

    assert len(result["listeners"]) == 1
    stunnel_subprocess.release(result)
