import click
import grpc
import uuid
import time
import sys
from .appcontroller import AppCtrl
from .appcontroller import IperfCtrl
from concurrent import futures
from globus_sdk import NativeAppAuthClient
from globus_sdk.scopes import ScopeBuilder
from .proto import scistream_pb2
from .proto import scistream_pb2_grpc
from . import utils
import importlib.metadata
__version__ = importlib.metadata.version('scistream-proto')

@click.group()
@click.version_option(__version__, '--version', '-v', help='Show the version and exit')
def cli():
    pass

linkprompt = "Please authenticate with Globus here"
def get_client():
    return NativeAppAuthClient('4787c84e-9c55-4881-b941-cb6720cea11c')

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
    try:
        tokens = utils.get_access_token(scope)
        if "INVALID_TOKEN" in tokens:
            raise utils.UnauthorizedError
        else:
            click.echo("You are already logged in, to try different credentials please log out!")
        return
    except utils.UnauthorizedError:
        click.echo("To obtain token for the scope, please open the URL in your browser and follow the instructions")

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
@click.option('--ip', default=None, help='IP address to fetch the scope and then get the access token.')
@click.option('--scope', default="c42c0dac-0a52-408e-a04f-5d31bfe0aef8", help='Directly provide the scope to get the access token.')
def check_auth(ip, scope):
    """
    Displays globus credentials for a given ip or scope.
    """
    if ip:
        scope = utils.get_scope_id(ip)
    if scope:
        token = utils.get_access_token(scope)
        click.echo(f"Access Token for scope '{scope}': {token}")

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
@click.option('--s2cs', default="localhost:5000")
@click.option('--server_cert', default="server.crt", help="Path to the server certificate file")
@utils.authorize
def release(uid, s2cs, server_cert, metadata=None):
    try:
        with open(server_cert, 'rb') as f:
            trusted_certs = f.read()
        credentials = grpc.ssl_channel_credentials(root_certificates=trusted_certs)
        with grpc.secure_channel(s2cs, credentials) as channel:
            stub = scistream_pb2_grpc.ControlStub(channel)
            msg = scistream_pb2.Release(uid=uid)
            resp = stub.release(msg, metadata=metadata)
            print("Release completed")
    except Exception as e:
        print(f"Error during release: {e}")

@cli.command()
@click.option('--num_conn', type=int, default=5)
@click.option('--rate', type=int, default=10000)
@click.option('--s2cs', default="localhost:5000")
@click.option('--server_cert', default="server.crt", help="Path to the server certificate file")
@click.option('--mock', default=False)
@click.option('--scope', default="")
def prod_req(num_conn, rate, s2cs, server_cert, mock, scope):
    with open(server_cert, 'rb') as f:
        trusted_certs = f.read()
        credentials = grpc.ssl_channel_credentials(root_certificates=trusted_certs)
    with grpc.secure_channel(s2cs, credentials) as channel:
        prod_stub = scistream_pb2_grpc.ControlStub(channel)
        
        uid = str(uuid.uuid1()) if not mock else "4f8583bc-a4d3-11ee-9fd6-034d1fcbd7c3"
        click.echo("uid; s2cs; access_token; role")
        if scope == "":
            scope = utils.get_scope_id(s2cs)
        click.echo(f"{uid} {s2cs} {utils.get_access_token(scope)} PROD")
        with futures.ThreadPoolExecutor(max_workers=2) as executor:
            click.echo("waiting for hello message")
            prod_resp_future = executor.submit(client_request, prod_stub, uid, "PROD", num_conn, rate, scope_id=scope)
            prod_resp = prod_resp_future.result()
        print(prod_resp)  # Should this be printed?
        # Extracting listeners
        prod_lstn = prod_resp.listeners
        prod_app_lstn = prod_resp.prod_listeners
        # Update the prod_stub
        update(prod_stub, uid, prod_resp.prod_listeners, "PROD", scope_id=scope)
        print(prod_resp.listeners)

@cli.command()
@click.option('--num_conn', type=int, default=5)
@click.option('--rate', type=int, default=10000)
@click.option('--s2cs', default="localhost:6000")
@click.option('--scope', default="")
@click.option('--server_cert', default="server.crt", help="Path to the server certificate file")
@click.argument("uid")
@click.argument("prod_lstn")
def cons_req(num_conn, rate, s2cs, scope, server_cert, uid, prod_lstn):  # uid and prod_lstn are dependencies from PROD context
    with open(server_cert, 'rb') as f:  
        trusted_certs = f.read()
        credentials = grpc.ssl_channel_credentials(root_certificates=trusted_certs)
    with grpc.secure_channel(s2cs, credentials) as channel:
        cons_stub = scistream_pb2_grpc.ControlStub(channel)
        if scope == "":
            scope = utils.get_scope_id(s2cs)
        click.echo(f"{uid} {s2cs} {utils.get_access_token(scope)} CONS")
        with futures.ThreadPoolExecutor(max_workers=2) as executor:
            cons_resp_future = executor.submit(client_request, cons_stub, uid, "CONS", num_conn, rate, scope_id=scope)
            cons_resp = cons_resp_future.result()
        cons_lstn = cons_resp.listeners
        # Update the cons_stub
        if ',' in prod_lstn:
            listener_array = prod_lstn.split(',')
        else:
            listener_array = [prod_lstn]
        update(cons_stub, uid, listener_array, "CONS", scope_id=scope)
        # prod_lstn is a dependency from PROD context


@utils.authorize
def client_request(stub, uid, role, num_conn, rate, scope_id="", metadata=None):
    """
    This behaves slightly different than release,
    release gets an IP:port tuple as input
    This receives the grpc stub
    Not sure what are the implications
    """
    try:
        print("started client request")
        request = scistream_pb2.Request(uid=uid, role=role, num_conn=num_conn, rate=rate)
        response = stub.req(request, metadata=metadata)
        return response
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.UNAUTHENTICATED:
            click.echo(f"Please obtain new credentials: {e.details()}")
            sys.exit(1)
        else:
            click.echo(f"Another GRPC error occurred: {e.details()}")

@utils.authorize
def update(stub, uid, remote_listeners, role= "PROD", scope_id="", metadata=None):
    """This behaves very similar to client_request"""
    try:
        update_request = scistream_pb2.UpdateTargets(uid=uid, remote_listeners=remote_listeners, role=role)
        stub.update(update_request, metadata=metadata)
    except Exception as e:
        print(f"Error during update: {e}")

if __name__ == '__main__':
    cli()
