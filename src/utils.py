import functools
import time
import logging
import sys
import traceback
from pathlib import Path

from globus_sdk.tokenstorage import SQLiteAdapter

from grpc import StatusCode

class ValidationException(Exception):
    ##
    pass

class UnauthorizedError(Exception):
    ##
    pass

class UnauthenticatedException(Exception):
    ##
    pass

class ForbiddenError(Exception):
    ##
    pass

def request_decorator(func):
    #assumes function has a self.logger
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = None
        self, request= args[0], args[1]

        if func.__name__ =="req":
            if self.resource_map.get(request.uid):
                raise ValidationException("Entry already found for uid")
        elif request.uid not in self.resource_map:
                raise ValidationException(f"{func.__name__} request invalid, entry not found for uid '{request.uid}'")
        try:
            self.logger.debug(f"{func.__name__} started, with request {request}")
            result = func(*args, **kwargs)
            self.logger.info(f"{func.__name__} completed")
        except Exception as e:
            self.logger.error(f"Error in function '{func.__name__}': {str(e)}")
            print(traceback.format_exc())
            raise e
        finally:
            end_time = time.time()
            duration = end_time - start_time
            self.logger.debug(f"{func.__name__} took {duration:.4f} seconds")
        return result

    return wrapper

def authenticated(func):
    """ Mark a route as requiring authentication """
    @functools.wraps(func)
    def decorated_function(*args, **kwargs):
        ## if client _secret has not been defined then we turn off credential validation
        self = args[0]
        if self.client_secret == "":
            return func(*args, **kwargs)
        context = args[2]
        metadata = dict(context.invocation_metadata())
        auth_token = metadata.get('authorization')
        error_message = f'scope_id {self.client_id}'
        if not auth_token:
            print(f'Authentication token is missing for scope_id {self.client_id}')
            context.abort(StatusCode.UNAUTHENTICATED, f'Authentication token is missing for scope {self.client_id}')
        if not self.validate_creds(auth_token):
            print(f'Authentication token is invalid for scope_id {self.client_id}')
            context.abort(StatusCode.UNAUTHENTICATED, f'Authentication token is invalid for scope {self.client_id}')
        return func(*args, **kwargs)
    return decorated_function

def authorize(func):
    """
    Authorize decorates a function and adds an authorization to the metadata header
    It must include a variable s2cs or scope_id for this to work
    it cannot support a function that has neither variables

    The decorator is used to separate the authorization logic from the rest of the code
    get_access_token is where the logic for storing and retrieving the access token is defined
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if "s2cs" in kwargs:
            scope_id = get_scope_id(kwargs["s2cs"])
        else:
            scope_id = kwargs["scope_id"]
        kwargs['metadata'] = (
            ('authorization', f'{get_access_token(scope_id)}'),
        )
        return func(*args, **kwargs)
    return wrapper

# TODO Create configuration subsystem instead of hardcoding CLIENT ID values
def get_scope_id(s2cs):
    scope_map={
        "10.16.42.61": "c42c0dac-0a52-408e-a04f-5d31bfe0aef8",
        "10.16.41.12": "26c25f3c-c4b7-4107-8a25-df96898a24fe",
        "10.16.42.31": "c42c0dac-0a52-408e-a04f-5d31bfe0aef8",
        "localhost": "c42c0dac-0a52-408e-a04f-5d31bfe0aef8",
        "127.0.0.1": "c42c0dac-0a52-408e-a04f-5d31bfe0aef8"
    }
    ip = s2cs.split(":")[0]

    return scope_map.get(ip, "")
    ## When IP is not found error silently, maybe not desirable

def storage_adapter():
    ## .storage.db hides this file
    ## maybe we should encrypt this?
    ## maybe we should ensure this is stored in a place only certain users can access it
    from globus_sdk.tokenstorage import SQLiteAdapter
    if not hasattr(storage_adapter, "_instance"):
        filename = f".storage.db"
        storage_adapter._instance = SQLiteAdapter(filename)
    return storage_adapter._instance
_cache={}

def get_access_token(scope_id):
    """
    This logic needs to be throughly tested

    Login, expects an exception when no scope is found.
    """
    if scope_id in _cache:
        return _cache[scope_id]
    tokens = storage_adapter().get_by_resource_server()
    if scope_id == "" or not tokens:
        # Assume authentication not required
        _cache[scope_id] = "INVALID_TOKEN"
        return "INVALID_TOKEN"
    if scope_id not in tokens:
        #Authentication missed
        raise UnauthorizedError()
    auth_data = tokens[scope_id]
    if auth_data and 'access_token' in auth_data:
        _cache[scope_id] = auth_data['access_token']
    else:
        _cache[scope_id] = "INVALID_TOKEN"
        raise UnauthorizedError()

    return auth_data['access_token']

def set_verbosity(self, verbose):
    #grpc_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    self.logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(fmt="%(message)s")
    self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler.setFormatter(formatter)
    self.logger.addHandler(handler)
