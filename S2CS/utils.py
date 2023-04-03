import functools
import time
import logging
import sys
import traceback

class ValidationException(Exception):
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

def set_verbosity(self, verbose):
    #grpc_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    self.logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(fmt="%(message)s")
    self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler.setFormatter(formatter)
    self.logger.addHandler(handler)
