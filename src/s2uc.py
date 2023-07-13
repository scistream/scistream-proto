import click
import grpc
import uuid
import time
import logging
import utils
from appcontroller import AppCtrl
from appcontroller import IperfCtrl
from concurrent import futures
from globus_sdk import NativeAppAuthClient
from globus_sdk import ConfidentialAppAuthClient
from proto import scistream_pb2
from proto import scistream_pb2_grpc

# Set up gRPC logging
#logging.basicConfig(level=logging.DEBUG)
#grpc_logger = logging.getLogger("grpc")
#grpc_logger.setLevel(logging.DEBUG)

@click.group()
def cli():
    pass

linkprompt = "Please authenticate with Globus here"

    # TODO Create configuration subsystem instead of hardcoding CLIENT ID values

@cli.command()
def login(s2cs):
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
    auth_client.oauth2_start_flow(refresh_tokens=True)

    click.echo("{0}:\n{1}\n{2}\n{1}\n".format(
        linkprompt,
        "-" * len(linkprompt),
        auth_client.oauth2_get_authorize_url(query_params={"prompt": "login"})
        )
    )
    auth_code = click.prompt("Enter the resulting Authorization Code here").strip()
    tkn=auth_client.oauth2_exchange_code_for_tokens(auth_code)
    adapter.store(tkn)

def get_auth_client():
    """Create a Globus Auth client from config info"""
    client = ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)
    return client


@cli.command()
def logout():
    """
    Logout of Globus

    This command both removes all tokens used for authenticating the user from local
    storage and revokes them so that they cannot be used anymore globally.
    """
    adapter = utils.storage_adapter()
    native_client = get_client()
    for rs, tokendata in adapter.remove_tokens_for_resource_server().items():
        for tok_key in ("access_token", "refresh_token"):
            token = tokendata[tok_key]
            native_client.oauth2_revoke_token(token)
        adapter.remove_tokens_for_resource_server(rs)
    click.echo("Successfully logged out!")

@cli.command()
def print_tokens():
    """CLI command to retrieve and print all tokens."""
    # Initialize the SQLiteAdapter
    adapter = utils.storage_adapter()
    all_tokens = adapter.get_by_resource_server()
    # Iterate over the tokens and print them
    for resource_server, token_data in all_tokens.items():
        click.echo(f"Resource server: {resource_server}")
        click.echo(f"Token Data: {token_data}")  # Print an empty line for readability

@cli.command()
def inspect_tokens():
    adapter = utils.storage_adapter()
    all_tokens = adapter.get_by_resource_server()
    native_client = get_client()
    token_meta2 = native_client.oauth2_validate_token(all_tokens['auth.globus.org']['access_token'])
    client = get_auth_client()
    token_meta = client.oauth2_validate_token(all_tokens['auth.globus.org']['refresh_token'])
    token_meta = client.oauth2_token_introspect(all_tokens['auth.globus.org']['refresh_token'])
    print(token_meta)

@cli.command()
@click.argument('uid', type=str, required=True)
@click.option('--producer-s2cs', default="localhost:5000")
@click.option('--consumer-s2cs', default="localhost:6000")
@click.option('--auth', is_flag=True)
def release(auth, creds, uid, producer_s2cs, consumer_s2cs):
    for s2cs in [producer_s2cs, consumer_s2cs]:
        try:
            with grpc.insecure_channel(s2cs) as channel:
                stub = scistream_pb2_grpc.ControlStub(channel)
                msg = scistream_pb2.Release(uid=uid)
                if auth:
                    token = utils.get_auth_token()
                    headers = (
                        ('authorization', f'Bearer {token}'),
                    )
                    resp = stub.release(msg, metadata=headers)
                else:
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
            consumer_future = executor.submit(AppCtrl, globus_auth, "CONS", consumer_s2cs)

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
            time.sleep(0.2)  # Possible race condition between REQ and HELLO
            producer_future = executor.submit(AppCtrl, uid, "PROD", s2cs)
            prod_resp = prod_resp_future.result()
            producer = producer_future.result()

        update(prod_stub, uid, prod_resp.prod_listeners)
        with futures.ThreadPoolExecutor(max_workers=4) as executor:
            consumer_future = executor.submit(AppCtrl, uid, "CONS", s2cs)
            consumer = consumer_future.result()
            ## APPctrl communicates with Scistream
            ## Scistream tells it what port it should send the data to

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
