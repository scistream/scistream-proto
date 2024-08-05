import os
import sys
import time
import socket
import subprocess
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.s2ds import StunnelSubprocess, get_config_path


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


@pytest.fixture(autouse=True)
def cleanup_processes():
    processes = []
    yield processes
    for proc in processes:
        proc.terminate()
        proc.wait()


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
    result = stunnel_subprocess.start(5, "127.0.0.1")
    assert len(result["listeners"]) == 5
    assert all(listener.startswith("127.0.0.1:") for listener in result["listeners"])
    assert result["s2ds_proc"] == []


def test_start_single(stunnel_subprocess):
    result = stunnel_subprocess.start(1, "127.0.0.1")
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
    uid = "test-uid"
    dest_array = ["192.168.1.1:443"]
    role = "CONS"
    stunnel_subprocess.start(5, "127.0.0.1")
    config_path = stunnel_subprocess.generate_stunnel_config(uid, dest_array, role)

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
    stunnel_subprocess.start(5, "127.0.0.1")
    stunnel_subprocess.update_listeners(listeners, s2ds_proc, uid, role)
    assert len(s2ds_proc) == 1
    if s2ds_proc[0].poll() is None:
        s2ds_proc[0].terminate()


def test_full_cycle(stunnel_subprocess):
    entry = stunnel_subprocess.start(5, "127.0.0.1")
    assert len(entry["listeners"]) == 5

    stunnel_subprocess.update_listeners(
        entry["listeners"], entry["s2ds_proc"], "test-uid", "CONS"
    )
    assert len(entry["s2ds_proc"]) == 1
    assert entry["s2ds_proc"][0].poll() is None

    stunnel_subprocess.release(entry)
    time.sleep(0.1)
    assert isinstance(entry["s2ds_proc"][0], int)


def test_start_multiple_subprocesses(stunnel_subprocess):
    result1 = stunnel_subprocess.start(5, "127.0.0.1")
    result2 = stunnel_subprocess.start(5, "127.0.0.1")

    assert len(result1["listeners"]) == 5
    assert len(result2["listeners"]) == 5
    assert all(
        listener.startswith("127.0.0.1:")
        for listener in result1["listeners"] + result2["listeners"]
    )
    assert len(set(result1["listeners"]).intersection(set(result2["listeners"]))) == 0

    stunnel_subprocess.update_listeners(
        result1["listeners"], result1["s2ds_proc"], "test-uid", "CONS"
    )
    stunnel_subprocess.update_listeners(
        result2["listeners"], result2["s2ds_proc"], "test-uid2", "CONS"
    )

    assert result1["s2ds_proc"][0].poll() is None
    assert result2["s2ds_proc"][0].poll() is None

    stunnel_subprocess.release(result1)
    stunnel_subprocess.release(result2)


def test_port_conflict(stunnel_subprocess):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        occupied_port = sock.getsockname()[1]

        with pytest.raises(Exception):
            stunnel_subprocess.start(1, "127.0.0.1", start_port=occupied_port)


def test_rapid_start_release_cycles(stunnel_subprocess):
    for _ in range(50):
        result = stunnel_subprocess.start(1, "127.0.0.1")
        assert len(result["listeners"]) == 1
        stunnel_subprocess.release(result)


def test_error_recovery(stunnel_subprocess, monkeypatch):
    def mock_popen(*args, **kwargs):
        raise OSError("Simulated error")

    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    with pytest.raises(OSError):
        stunnel_subprocess.start(1, "127.0.0.1")

    monkeypatch.undo()
    result = stunnel_subprocess.start(1, "127.0.0.1")

    assert len(result["listeners"]) == 1
    stunnel_subprocess.release(result)
