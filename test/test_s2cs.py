import sys
import pytest
import threading
import time
from unittest import mock
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/ "src"))

from concurrent import futures
from proto.scistream_pb2 import Request, AppResponse, Response, UpdateTargets, Hello
from s2cs import S2CS, S2CSException, S2DS

class MockS2DS(S2DS):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start(self, num_conn, listener_ip):
        # Define your mocked behavior here
        return {
            "s2ds_proc": [mock.MagicMock() for _ in range(num_conn)],
            "listeners": [f"{listener_ip}:500{i}" for i in range(num_conn)]
        }

    def release(self, entry):
        # Define your mocked behavior here (if needed)
        pass

    def update_listeners(self, listeners, s2ds_proc):
        # Define your mocked behavior here (if needed)
        pass

@pytest.fixture(scope='function')
def servicer():
    s2cs = S2CS(listener_ip='127.0.0.1', verbose=False)
    s2cs.s2ds = MockS2DS()
    return s2cs

@pytest.mark.timeout(5)
def test_update_success(servicer):
    ### Expand test conditions
    # Simulate an existing entry in the resource_map
    servicer.resource_map['test_uid'] = {
        "role": "CONS",
        "num_conn": 1,
        "rate": 1,
        "hello_received": threading.Event(),
        "s2ds_proc": mock.MagicMock(),
        "listeners": ["127.0.0.1:5001"]
    }
    update_request = UpdateTargets(uid='test_uid', remote_listeners=['127.0.0.1:47000'])
    response = servicer.update(update_request, None)
    assert response.listeners

#Expected to fail
@pytest.mark.xfail
@pytest.mark.timeout(5)
def test_req_no_hello(servicer):
    request = Request(uid='test_uid', role='PROD', num_conn=1, rate=1)
    response = servicer.req(request, None)
    assert response.listeners

@pytest.mark.timeout(5)
def test_req_timeout(servicer):
    request = Request(uid='test_uid', role='PROD', num_conn=1, rate=1)
    with mock.patch.object(S2CS, "TIMEOUT", 0):
        with pytest.raises(S2CSException) as excinfo:
            response = servicer.req(request, None)
        assert "Hello not received within the timeout period" in str(excinfo.value)

@pytest.mark.timeout(5)
def test_release_success(servicer):
    # Simulate an existing entry in the resource_map
    servicer.resource_map['test_uid'] = {
        "role": "CONS",
        "num_conn": 1,
        "rate": 1,
        "hello_received": threading.Event(),
        "s2ds_proc": mock.MagicMock()
    }

    release_request = Request(uid='test_uid')
    response = servicer.release(release_request, None)
    assert "test_uid" not in servicer.resource_map

@pytest.mark.timeout(5)
def test_req_and_hello(servicer):
    hello_request = Hello(uid='test_uid', prod_listeners=['127.0.0.1:5000'])
    req_request = Request(uid='test_uid', role='PROD', num_conn=1, rate=1)
    with futures.ThreadPoolExecutor(max_workers=2) as executor:
        req_future = executor.submit(lambda: servicer.req(req_request, None))
        time.sleep(0.5)
        hello_future = executor.submit(lambda: servicer.hello(hello_request, None))
        hello_response = hello_future.result(timeout=2)
        req_response = req_future.result(timeout=2)
    assert servicer.resource_map['test_uid']

@pytest.mark.timeout(5)
def test_hello_success(servicer):
    servicer.resource_map['test_uid'] = {
        "role": "PROD",
        "num_conn": 1,
        "rate": 1,
        "hello_received": threading.Event(),
        "s2ds_proc": mock.MagicMock(),
        "listeners": ["127.0.0.1:5001"]
    }

    hello_request = Hello(uid='test_uid', prod_listeners=['127.0.0.1:7000'])
    response = servicer.hello(hello_request, None)
    assert response.message
