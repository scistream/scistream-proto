import functools
import time
import logging
import sys
import traceback

from globus_sdk.tokenstorage import SQLiteAdapter

from grpc import StatusCode

class ValidationException(Exception):
    ##
    pass

class UnauthorizedError(Exception):
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
                raise ValidationException(f"{func.__name__} validation failed, entry not found for uid '{request.uid}'")
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
        context = args[2]
        self = args[0]
        metadata = dict(context.invocation_metadata())
        auth_token = metadata.get('authorization')
        if not auth_token:
            context.abort(StatusCode.UNAUTHENTICATED, 'Authentication token is missing')
        if not self.validate_creds(auth_token):
            context.abort(StatusCode.UNAUTHENTICATED, f"Authentication token is invalid")
        return func(*args, **kwargs)
    return decorated_function

def authorize(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        #print("started client authorization")
        kwargs['metadata'] = (
            ('authorization', f'{get_access_token()}'),
        )
        return func(*args, **kwargs)
    return wrapper

def storage_adapter():
    from globus_sdk.tokenstorage import SQLiteAdapter
    if not hasattr(storage_adapter, "_instance"):
        filename = "storage.db"
        ## TODO Hardcoded must be changed in the future
        storage_adapter._instance = SQLiteAdapter(filename)
    return storage_adapter._instance
_cache={}

def get_access_token():
    if 'token' in _cache:
        #print("retrieving from CACHE")
        return _cache['token']
    auth_data = storage_adapter().get_token_data('c42c0dac-0a52-408e-a04f-5d31bfe0aef8')
    if auth_data:
        _cache['token']=auth_data['access_token']
        #print("Stored in cache")
    else:
        #print("Token not found")
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
