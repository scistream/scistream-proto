import click
import functools
import uuid
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from appcontroller import AppCtrl
import grpc

import scistream_pb2
import scistream_pb2_grpc

# Set up gRPC logging
logging.basicConfig(level=logging.DEBUG)
grpc_logger = logging.getLogger("grpc")
grpc_logger.setLevel(logging.DEBUG)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('num_conn', type=int, default=5, required=False)
@click.argument('rate', type=int, default=10000, required=False)
@click.argument('producer_s2cs', default="localhost:5000", required=False)
@click.argument('consumer_s2cs', default="localhost:6000", required=False)
def request(num_conn, rate, producer_s2cs, consumer_s2cs):
    with grpc.insecure_channel(producer_s2cs) as channel1, \
      grpc.insecure_channel(consumer_s2cs) as channel2:
        prod_stub = scistream_pb2_grpc.ControlStub(channel1)
        cons_stub = scistream_pb2_grpc.ControlStub(channel2)

        request = scistream_pb2.Request(
            uid=str(uuid.uuid1()),
            role="PROD",
            num_conn=num_conn,
            rate=rate
        )
        with ThreadPoolExecutor(max_workers=4) as executor:
            prod_resp_future = executor.submit(client_request, prod_stub, request)
            request.role = "CONS"
            cons_resp_future = executor.submit(client_request, cons_stub, request)
            time.sleep(0.1)  # Possible race condition between REQ and HELLO
            producer_future = executor.submit(AppCtrl, request.uid, "PROD", producer_s2cs)
            consumer_future = executor.submit(AppCtrl, request.uid, "CONS", consumer_s2cs)

            prod_resp = prod_resp_future.result()
            cons_resp = cons_resp_future.result()
            producer = producer_future.result()
            consumer = consumer_future.result()

        print(prod_resp)
        prod_lstn = prod_resp.listeners
        prod_app_lstn = prod_resp.prod_listeners
        cons_lstn = cons_resp.listeners

        print("Sending updated connection map information...")
        update(prod_stub, request.uid, prod_app_lstn)
        update(cons_stub, request.uid, prod_lstn)


def client_request(stub, request):
    try:
        response = stub.req(request)
        return response
    except Exception as e:
        print(f"Error during client_request: {e}")
        return None


def update(stub, uid, remote_listeners):
    try:
        update_request = scistream_pb2.UpdateTargets(uid=uid, remote_listeners=remote_listeners)
        stub.update(update_request)
    except Exception as e:
        print(f"Error during update: {e}")


if __name__ == '__main__':
    cli()

class S2client():

    def __init__(self, producer_s2cs, consumer_s2cs):
        channel1 = Channel(producer_s2cs)
        self.producer_s2cs = scistream_pb2_grpc.ControlStub(channel1)
        channel2 = Channel(consumer_s2cs)
        self.consumer_s2cs = scistream_pb2_grpc.ControlStub(channel2)

    def updateTargets(self, stub, uid, local_listeners, remote_listeners):
        request = scistream_pb2.UpdateTargets(
            uid=uid,
            remote_listeners=remote_listeners
        )
        response = stub.update(request)
        assert response.status != "ERROR", response.status
        print("Connection map information successfully updated")

    def req(self,num_conn, rate, producer_s2cs, consumer_s2cs):
        request = scistream_pb2.Request(
            uid=str(uuid.uuid1()),
            role="PROD",
            num_conn=num_conn,
            rate=rate
        )
        prod_resp = self.producer_s2cs.request(request)
        request.role = "CONS"
        cons_resp = self.consumer_s2cs.request(request)

        app = AppCtrl(uid, '5000', '6000')

        prod_lstn = prod_resp.listeners
        prod_app_lstn = prod_resp.prod_listeners
        cons_lstn = cons_resp.listeners

        print("Sending updated connection map information...")
        self.update(self.producer_s2cs, uid, prod_lstn, prod_app_lstn)
        self.update(self.consumer_s2cs, uid, cons_lstn, prod_lstn)
        return request.uid

    def rel(self, uid):
        print("S2UC STARTED THIS")
        start = time.time()
        ## validate inputs
        assert uid != None and uid != "", "Invalid uid '%s'" % uid
        msg = scistream_pb2.Release(
            uid=uid
        )
        prod_resp = self.producer_s2cs.release(msg)
        cons_resp = self.consumer_s2cs.release(msg)
        print("Producer response: %s" % prod_resp)
        print("Consumer response: %s" % cons_resp)
        t = time.time() - start
        print("*** Process time: %s sec." % t)
