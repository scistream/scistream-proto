import click
import grpc
import uuid
import time
import utils
from appcontroller import AppCtrl
from appcontroller import IperfCtrl
from concurrent import futures
from globus_sdk import NativeAppAuthClient
from globus_sdk.scopes import ScopeBuilder
from proto import scistream_pb2
from proto import scistream_pb2_grpc

@click.group()
def cli():
    pass

linkprompt = "Please authenticate with Globus here"
def get_client():
    return NativeAppAuthClient('4787c84e-9c55-4881-b941-cb6720cea11c')
# TODO Create configuration subsystem instead of hardcoding CLIENT ID values

@cli.command()
@click.option('--scope', default="c42c0dac-0a52-408e-a04f-5d31bfe0aef8")
def login(scope):
    """
    Get globus credentials for the Scistream User Client.

    This command directs you to the page necessary to permit S2UC to make API
    calls for you, and gets the OAuth2 tokens needed to use those permissions.

    The CLI will print a link for you to manually follow to the Globus
    authorization page. After consenting you will then need to copy and paste the
    given access code from the web to the CLI.
    """
    adapter = utils.storage_adapter()

    if adapter.get_by_resource_server():
        click.echo("You are already logged in!")
        return
    auth_client = get_client()
    StreamScopes = ScopeBuilder(scope, known_url_scopes=["scistream"])
    auth_client.oauth2_start_flow(requested_scopes=[StreamScopes.scistream], refresh_tokens=True)
    click.echo("{0}:\n{1}\n{2}\n{1}\n".format(
        linkprompt,
        "-" * len(linkprompt),
        auth_client.oauth2_get_authorize_url(query_params={"prompt": "login"})
        )
    )
    auth_code = click.prompt("Enter the resulting Authorization Code here").strip()
    tkn=auth_client.oauth2_exchange_code_for_tokens(auth_code)
    adapter.store(tkn)

@cli.command()
def logout():
    """
    Logout of Globus

    This command both removes all tokens used for authenticating the user from local
    storage and revokes them so that they cannot be used anymore globally.
    """
    adapter = utils.storage_adapter()
    native_client = get_client()
    for rs, tokendata in adapter.get_by_resource_server().items():
        for tok_key in ("access_token", "refresh_token"):
            token = tokendata[tok_key]
            native_client.oauth2_revoke_token(token)
        adapter.remove_tokens_for_resource_server(rs)
    click.echo("Successfully logged out!")


@cli.command()
@click.argument('uid', type=str, required=True)
@click.option('--producer-s2cs', default="localhost:5000")
@click.option('--consumer-s2cs', default="localhost:6000")
@utils.authorize
def release(uid, producer_s2cs, consumer_s2cs, metadata=None):
    for s2cs in [producer_s2cs, consumer_s2cs]:
        try:
            with grpc.insecure_channel(s2cs) as channel:
                stub = scistream_pb2_grpc.ControlStub(channel)
                msg = scistream_pb2.Release(uid=uid)
                resp = stub.release(msg, metadata=metadata)
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
            time.sleep(0.5)  # Possible race condition between REQ and HELLO
            producer_future = executor.submit(AppCtrl, uid, "PROD", producer_s2cs, utils.get_access_token())
            consumer_future = executor.submit(AppCtrl, uid, "CONS", consumer_s2cs, utils.get_access_token())

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
        update(prod_stub, uid, prod_resp.prod_listeners)
        update(cons_stub, uid, prod_resp.listeners)

@cli.command()
@click.option('--num_conn', type=int, default=5)
@click.option('--rate', type=int, default=10000)
@click.option('--s2cs', default="localhost:5000")
def request1(num_conn, rate, s2cs):
    with grpc.insecure_channel(s2cs) as channel1:
        prod_stub = scistream_pb2_grpc.ControlStub(channel1)
        uid=str(uuid.uuid1())
        with futures.ThreadPoolExecutor(max_workers=4) as executor:

            prod_resp_future = executor.submit(client_request, prod_stub, uid, "PROD", num_conn, rate)
            time.sleep(0.1)  # Possible race condition between REQ and HELLO
            producer_future = executor.submit(AppCtrl, uid, "PROD", s2cs, utils.get_access_token())
            prod_resp = prod_resp_future.result()
            producer = producer_future.result()


        update(prod_stub, uid, prod_resp.prod_listeners)
        with futures.ThreadPoolExecutor(max_workers=4) as executor:
            consumer_future = executor.submit(AppCtrl, uid, "CONS", s2cs, utils.get_access_token())
            consumer = consumer_future.result()
            ## APPctrl communicates with Scistream
            ## Scistream tells it what port it should send the data to
        print(uid)

@cli.command()
@click.option('--num_conn', type=int, default=5)
@click.option('--rate', type=int, default=10000)
@click.option('--s2cs', default="localhost:5000")
def request2(num_conn, rate, s2cs, access_code):
    with grpc.insecure_channel(s2cs) as channel1:
        prod_stub = scistream_pb2_grpc.ControlStub(channel1)
        uid=str(uuid.uuid1())
        with futures.ThreadPoolExecutor(max_workers=4) as executor:
            prod_resp_future = executor.submit(client_request, prod_stub, uid, "PROD", num_conn, rate)
            time.sleep(0.2)  # Possible race condition between REQ and HELLO
            producer_future = executor.submit(IperfCtrl, uid, "PROD", s2cs)
            prod_resp = prod_resp_future.result()
            producer = producer_future.result()
        update(prod_stub, uid, prod_resp.prod_listeners)
        with futures.ThreadPoolExecutor(max_workers=4) as executor:
            consumer_future = executor.submit(IperfCtrl, uid, "CONS", s2cs)
            consumer = consumer_future.result()
            ## APPctrl communicates with Scistream
            ## Scistream tells it what port it should send the data to
@utils.authorize
def client_request(stub, uid, role, num_conn, rate, metadata=None):
    try:
        print("started client request")
        request = scistream_pb2.Request(uid=uid, role=role, num_conn=num_conn, rate=rate)
        response = stub.req(request, metadata=metadata)
        return response
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.UNAUTHENTICATED:
            click.ClickException(f"Authentication error for server scope, please obtain new credentials: {e.details()}")
        else:
            click.ClickException(f"Another GRPC error occurred: {e.details()}")

@utils.authorize
def update(stub, uid, remote_listeners, metadata=None):
    try:
        update_request = scistream_pb2.UpdateTargets(uid=uid, remote_listeners=remote_listeners)
        stub.update(update_request, metadata=metadata)
    except Exception as e:
        print(f"Error during update: {e}")

if __name__ == '__main__':
    cli()
