import sys
import pytest
import threading
import time
from unittest import mock
from unittest.mock import MagicMock
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

class MockContext(MagicMock):
    def invocation_metadata(self):
        from globus_sdk.tokenstorage import SQLiteAdapter
        auth_data = SQLiteAdapter('fixtures.db').get_token_data('auth.globus.org')
        return [('authorization', f'Bearer {auth_data["access_token"]}')]

    def abort(self, code, details):
        raise ValueError(f"Aborted with code {code} and details {details}")

@pytest.fixture(scope='function')
def context():
    return MockContext()

@mock.patch.object(S2CS, "validate_creds", return_value=True)
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
@mock.patch.object(S2CS, "validate_creds", return_value=True)
def test_req_no_hello(servicer):
    with mock.patch.object(S2CS, "validate_creds", return_value=True) as _:
        request = Request(uid='test_uid', role='PROD', num_conn=1, rate=1)
        response = servicer.req(request, None)
        assert response.listeners

@pytest.mark.timeout(5)
def test_req_timeout(servicer, context):
    request = Request(uid='test_uid', role='PROD', num_conn=1, rate=1)
    with mock.patch.object(S2CS, "TIMEOUT", 0):
        with mock.patch.object(S2CS, "validate_creds", return_value=True) as _:
            with pytest.raises(S2CSException) as excinfo:
                response = servicer.req(request, context)
                assert "Hello not received within the timeout period" in str(excinfo.value)

@mock.patch.object(S2CS, "validate_creds", return_value=True)
@pytest.mark.timeout(5)
def test_release_success(servicer, context):
    # Simulate an existing entry in the resource_map
    servicer.resource_map['test_uid'] = {
        "role": "CONS",
        "num_conn": 1,
        "rate": 1,
        "hello_received": threading.Event(),
        "s2ds_proc": mock.MagicMock()
    }

    release_request = Request(uid='test_uid')
    response = servicer.release(release_request, context)
    assert "test_uid" not in servicer.resource_map

@mock.patch.object(S2CS, "validate_creds", return_value=True)
@pytest.mark.timeout(5)
def test_req_and_hello(servicer):
    hello_request = Hello(uid='test_uid', role='PROD', prod_listeners=['10.0.0.1:5000'])
    req_request = Request(uid='test_uid', role='PROD', num_conn=1, rate=1)
    with futures.ThreadPoolExecutor(max_workers=2) as executor:
        req_future = executor.submit(lambda: servicer.req(req_request, None))
        time.sleep(0.5)
        hello_future = executor.submit(lambda: servicer.hello(hello_request, None))
        hello_response = hello_future.result(timeout=2)
        req_response = req_future.result(timeout=2)
    assert servicer.resource_map['test_uid']

@pytest.mark.timeout(5)
@mock.patch.object(S2CS, "validate_creds", return_value=True)
def test_full_request(servicer):
    hello_request = Hello(uid='test_uid', role='PROD', prod_listeners=['10.0.0.1:5000'])
    req_request = Request(uid='test_uid', role='PROD', num_conn=1, rate=1)
    with futures.ThreadPoolExecutor(max_workers=2) as executor:
        req_future = executor.submit(lambda: servicer.req(req_request, None))
        time.sleep(0.5)
        hello_future = executor.submit(lambda: servicer.hello(hello_request, None))
        hello_response = hello_future.result(timeout=2)
        req_response = req_future.result(timeout=2)
    update_request = UpdateTargets(uid='test_uid', role='PROD', remote_listeners=req_response.prod_listeners)
    servicer.update( update_request, None )
    print(servicer.resource_map)
    assert servicer.resource_map['test_uid']

@mock.patch.object(S2CS, "validate_creds", return_value=True)
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

def test_validation(servicer, context):
    meta = dict(context.invocation_metadata())
    auth_token = meta.get('authorization')
    validate = servicer.validate_creds(auth_token)
    assert validate
