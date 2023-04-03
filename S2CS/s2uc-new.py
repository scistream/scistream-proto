import click
import grpc
import uuid
import time
import logging
import scistream_pb2
import scistream_pb2_grpc
from concurrent import futures
from appcontroller import AppCtrl

# Set up gRPC logging
logging.basicConfig(level=logging.DEBUG)
grpc_logger = logging.getLogger("grpc")
grpc_logger.setLevel(logging.DEBUG)

@click.group()
def cli():
    pass

@cli.command()
@click.argument('uid', type=str, required=True)
@click.option('--producer-s2cs', default="localhost:5000")
@click.option('--consumer-s2cs', default="localhost:6000")
def release(uid, producer_s2cs, consumer_s2cs):
    for s2cs in [producer_s2cs, consumer_s2cs]:
        try:
            with grpc.insecure_channel(s2cs) as channel:
                stub = scistream_pb2_grpc.ControlStub(channel)
                msg = scistream_pb2.Release(uid=uid)
                resp = stub.release(msg)
                print("Release completed")
        except Exception as e:
            print(f"Error during release: {e}")

@cli.command()
@click.option('--num_conn', type=int, default=5)
@click.option('--rate', type=int, default=10000)
@click.option('--producer-s2cs', default="localhost:5000")
@click.option('--consumer-s2cs', default="localhost:6000")
def request(num_conn, rate, producer_s2cs, consumer_s2cs):
    with grpc.insecure_channel(producer_s2cs) as channel1, \
      grpc.insecure_channel(consumer_s2cs) as channel2:
        prod_stub = scistream_pb2_grpc.ControlStub(channel1)
        cons_stub = scistream_pb2_grpc.ControlStub(channel2)
        uid=str(uuid.uuid1())
        with futures.ThreadPoolExecutor(max_workers=4) as executor:
            prod_resp_future = executor.submit(client_request, prod_stub, uid, "PROD", num_conn, rate)
            cons_resp_future = executor.submit(client_request, cons_stub, uid, "CONS", num_conn, rate)
            time.sleep(0.1)  # Possible race condition between REQ and HELLO
            producer_future = executor.submit(AppCtrl, uid, "PROD", producer_s2cs)
            consumer_future = executor.submit(AppCtrl, uid, "CONS", consumer_s2cs)

            prod_resp = prod_resp_future.result()
            cons_resp = cons_resp_future.result()
            producer = producer_future.result()
            consumer = consumer_future.result()

        print(prod_resp) ## Should this be printed?
        prod_lstn = prod_resp.listeners
        prod_app_lstn = prod_resp.prod_listeners
        cons_lstn = cons_resp.listeners

        print("Sending updated connection map information...")
        print(uid)
        update(prod_stub, uid, prod_app_lstn)
        update(cons_stub, uid, prod_lstn)

def client_request(stub, uid, role, num_conn, rate):
    try:
        request = scistream_pb2.Request(uid=uid, role=role, num_conn=num_conn, rate=rate)
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
