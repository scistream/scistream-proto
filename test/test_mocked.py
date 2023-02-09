
import pickle
import concurrent.futures
import time
import threading
import pathlib
import subprocess
import shlex
import sys
import test.context as context
from test.context import s2uc
import pytest
import S2UC.s2uc

class clientMocked(s2uc.S2client):

    def sendmsg(self,msg,other):
        a=context.mocksocket()
        a.send(pickle.dumps(msg))
        return a

    def notifyAppCtrl( self, uid, prod_app_port, cons_app_port):
        ## Actually mocking an app controller here
        # TODO: Remove hard-coded prod_app_listeners and ProdApp->S2CS ports
        python_script = pathlib.Path.cwd()/'test/send_hello_mocked.py'## doesn't work
        prod_app_listeners = ['127.0.0.1:7000', '127.0.0.1:17000', '127.0.0.1:27000', '127.0.0.1:37000', '127.0.0.1:47000']
        temp_prod_cli = ['python', str(python_script), '--s2cs-port', prod_app_port, '--uid', str(uid)]
        for l in prod_app_listeners:
            temp_prod_cli.extend(['--prod-listener', l])
        temp_cons_cli = ['python', str(python_script), '--s2cs-port', cons_app_port, '--uid', str(uid)]
        subprocess.run(temp_prod_cli)
        subprocess.run(temp_cons_cli)

def test_req():
    clientMocked().req(5,10000,"localhost:5000","localhost:6000")

def test_mocked():
    client=clientMocked()
    uid=client.req(5,10000,"localhost:5000","localhost:6000")
    client.rel(uid,"localhost:5000","localhost:6000")

def test_integrated():
    try:
        cli = "python S2CS/s2cs.py --s2-port=5000 --app-port=5500 --listener-ip=127.0.0.1"
        p1=subprocess.Popen(shlex.split(cli))
        cli2 = "python S2CS/s2cs.py --s2-port=6000 --app-port=6500 --listener-ip=127.0.0.1"
        p2=subprocess.Popen(shlex.split(cli2))
        time.sleep(0.5)
        client=s2uc.S2client()
        uid=client.req(5,10000,"localhost:5000", "localhost:6000")
        time.sleep(0.5)
        client.rel(uid,"localhost:5000","localhost:6000")
    finally:
        p1.kill()
        p2.kill()

def test_threadsingleclient():
    try:
        cli = "python S2CS/s2cs.py --s2-port=5000 --app-port=5500 --listener-ip=127.0.0.1"
        p1=subprocess.Popen(shlex.split(cli))
        cli2 = "python S2CS/s2cs.py --s2-port=6000 --app-port=6500 --listener-ip=127.0.0.1"
        p2=subprocess.Popen(shlex.split(cli2))
        time.sleep(0.2)
        def req():
            client=s2uc.S2client()
            uid=client.req(5,10000,"localhost:5000", "localhost:6000")
            return uid
            time.sleep(0.1)
            client.rel(uid,"localhost:5000","localhost:6000")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = [executor.submit(req) for i in range(0,1)]
        time.sleep(1)
        results = [r.result(0.5) for r in results]
    finally:
        p1.kill()
        p2.kill()
        assert len(results) > 0

@pytest.mark.skip(reason="no way of currently testing this")
def test_threadmulticlient():
    ## TODO lacking assertion
    try:
        cli = "python S2CS/s2cs.py --s2-port=5000 --app-port=5500 --listener-ip=127.0.0.1"
        p1=subprocess.Popen(shlex.split(cli))
        cli2 = "python S2CS/s2cs.py --s2-port=6000 --app-port=6500 --listener-ip=127.0.0.1"
        p2=subprocess.Popen(shlex.split(cli2))
        time.sleep(0.5)
        def req():
            client=s2uc.S2client()
            uid=client.req(5,10000,"localhost:5000", "localhost:6000")
            return uid
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = [executor.submit(req) for i in range(0,10)]
        time.sleep(5)
        results = [r.result(1) for r in results]
    finally:
        print("PRINTING RESULTS")
        print(results)
        p1.kill()
        p2.kill()
