"""

"""
import time
import sys
import zmq
import subprocess
import pickle
import uuid
import pathlib
import fire

class S2client():

    # TODO: Remove hard-coded prod_app_listeners and ProdApp->S2CS ports
    def notifyAppCtrl(self, uid, prod_app_port, cons_app_port):
        #make it private
        ## Actually mocking an app controller here
        python_script = pathlib.Path.cwd()/'utils/send_hello.py'
        prod_app_listeners = ['127.0.0.1:7000', '127.0.0.1:17000', '127.0.0.1:27000', '127.0.0.1:37000', '127.0.0.1:47000']
        temp_prod_cli = ['python', str(python_script), '--s2cs-port', prod_app_port, '--uid', str(uid)]
        for l in prod_app_listeners:
            temp_prod_cli.extend(['--prod-listener', l])
        temp_cons_cli = ['python', str(python_script), '--s2cs-port', cons_app_port, '--uid', str(uid)]
        subprocess.run(temp_prod_cli)
        subprocess.run(temp_cons_cli)

    def updateTargets(self, endpoint, uid, local_listeners, remote_listeners):
        msg = {
                "cmd": "UpdateTargets",
                "uid": uid,
                "local_listeners": local_listeners,
                "remote_listeners": remote_listeners
            }
        endpoint.send(pickle.dumps(msg))
        resp = pickle.loads(endpoint.recv())
        assert str(resp)[:6] != "ERROR:", resp
        print("Connection map information successfully updated")

    def sendmsg(self,msg,target):
        socket = zmq.Context().socket(zmq.REQ)
        socket.connect("tcp://%s" % target)
        socket.send(pickle.dumps(msg))
        return socket

    def req(self,num_conn, rate, prod_s2cs, cons_s2cs):
        print("S2UC STARTED THIS")
        start = time.time()
        ## validate inputs
        uid = str(uuid.uuid1())
        assert num_conn != None and int(num_conn) > 0, "Invalid number of connections '%s'" % num_conn
        assert rate != None and int(rate) > 0, "Invalid rate '%s'" % rate
        assert uid != None and uid != "", "Invalid uid '%s'" % uid
        print(uid)
        cmd = "REQ"
        req = {
                'cmd': cmd,
                'uid': uid,
                'num_conn': num_conn,
                'rate': rate
        }
        print("S2UC Requesting producer resources...")
        req["role"] = "PROD"
        prod_s2cs = self.sendmsg(req,prod_s2cs) #variable overload

        print("S2UC Requesting consumer resources...")
        req["role"] = "CONS"
        cons_s2cs = self.sendmsg(req,cons_s2cs)
        self.notifyAppCtrl(uid, '5500', '6500')

        prod_resp = pickle.loads(prod_s2cs.recv())
        cons_resp = pickle.loads(cons_s2cs.recv())

        prod_lstn = prod_resp["listeners"]
        prod_app_lstn = prod_resp["prod_listeners"]
        cons_lstn = cons_resp["listeners"]
        print("Sending updated connection map information...")
        self.updateTargets(prod_s2cs, uid, prod_lstn, prod_app_lstn)
        self.updateTargets(cons_s2cs, uid, cons_lstn, prod_lstn)


        prod_s2cs.close()
        cons_s2cs.close()
        t = time.time() - start
        print("*** Process time: %s sec." % t)
        return uid

    def rel(self, uid, prod_s2cs, cons_s2cs):
        print("S2UC STARTED THIS")
        start = time.time()
        ## validate inputs
        assert uid != None and uid != "", "Invalid uid '%s'" % uid
        req = {
                'cmd': "REL",
                'uid': uid
        }
        print("S2UC Releasing producer resources...")
        prod_s2cs = self.sendmsg(req,prod_s2cs)  #Transition 3

        print("S2UC Releasing consumer resources...")
        cons_s2cs = self.sendmsg(req,cons_s2cs)

        prod_resp = pickle.loads(prod_s2cs.recv())
        cons_resp = pickle.loads(cons_s2cs.recv())
        print("Producer response: %s" % prod_resp)
        print("Consumer response: %s" % cons_resp)
        prod_s2cs.close()
        cons_s2cs.close()
        t = time.time() - start
        print("*** Process time: %s sec." % t)

if __name__ == '__main__':
    fire.Fire(S2client)
