# Usage appcontroller.py uid_value PROD localhost:5000
import grpc
import scistream_pb2
import scistream_pb2_grpc

class AppCtrl():

    def __init__(self, uid, role, s2cs):
        ## Actually mocking an app controller call here
        # TODO catch connection error
        request = scistream_pb2.Hello(
            uid=uid
        )
        if role == "PROD":
            request.prod_listeners.extend(['127.0.0.1:7000', '127.0.0.1:17000', '127.0.0.1:27000', '127.0.0.1:37000', '127.0.0.1:47000'])
        with grpc.insecure_channel(s2cs) as channel2:
            s2cs = scistream_pb2_grpc.ControlStub(channel2)
            response = s2cs.hello(request)

if __name__ == '__main__':
    fire.Fire(AppCtrl)
