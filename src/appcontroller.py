# Usage appcontroller.py uid_value PROD localhost:5000
import click
import grpc
import zmq
import subprocess
import time
from proto import scistream_pb2
from proto import scistream_pb2_grpc

class AppCtrl():
    def __init__(self, uid, role, s2cs):
        ## Actually mocking an app controller call here
        # TODO catch connection error
        request = scistream_pb2.Hello(
            uid=uid
        )
        if role == "PROD":
            request.prod_listeners.extend(['127.0.0.1:7000', '127.0.0.1:17000', '127.0.0.1:27000', '127.0.0.1:37000', '127.0.0.1:47000'])
        with grpc.insecure_channel(s2cs) as channel:
            s2cs = scistream_pb2_grpc.ControlStub(channel)
            request.role = role
            self.response = s2cs.hello(request)
        self.start_app(role)

    def start_app(self, role):
        if role == "PROD":
            producer_process = subprocess.Popen(["python", __file__, "run-producer", "7000"])
        else:
            ## need some type of communication with S2CS to identify what port would the communication work
            consumer_process = subprocess.Popen(
                ["python", __file__,
                "subscribe",
                self.response.listeners[0]
                ]
            )

class IperfCtrl(AppCtrl):
    def start_app(self, role):
        if role == "PROD":
            producer_process = subprocess.Popen(["python", __file__, "iperf-server", "7000"])
        else:
            ## need some type of communication with S2CS to identify what port would the communication work
            consumer_process = subprocess.Popen(
                ["python", __file__,
                "iperf-client",
                self.response.listeners[0]
                ]
            )

class ProducerApplication():
    def __init__(self, port):
        self.port=port

class ZmqProd(ProducerApplication):
    def __init__(self, port):
        self.port=port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind("tcp://127.0.0.1:" + port)

    def start(self):
        for index in range(3600):
            time.sleep(0.05)
            _msg = 'NASDA:' + '%04dth message from publisher @ %s' % (index, time.strftime('%H:%M:%S'))
            self.socket.send_string( _msg )
        self.socket.send_string('NASDA:STOP')

class ZmqConsumerApplication():
    def __init__(self, target):
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(f"tcp://{target}")
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")

    def start(self):
        while True:
            # Receive messages
            message = self.subscriber.recv_string()
            #print("Received message: %s" % message)
            if message == 'NASDA:STOP':
                with open('log', 'w') as f: f.write('transfer completed')
                break
        self.subscriber.close()  # close socket when done

@click.group()
def cli():
    pass

@cli.command()
@click.argument('target', type=str, default="127.0.0.1:7000")
def subscribe(target):
    consumer = ZmqConsumerApplication(target=target)
    with open('cons.log', 'w') as f: f.write('consumer started')
    consumer.start()

@cli.command()
@click.argument('port', type=str, default="7000")
def run_producer(port):
    producer = ZmqProd(port=port)
    with open('prod.log', 'w') as f: f.write('producer started')
    producer.start()

@cli.command()
@click.argument('port', type=str, default="7000")
def iperf_server(port):
    try:
        iperf_process = subprocess.Popen(['iperf', '-s', '-p', str(port)])  # starts iperf in server mode on a specified port
        with open('iperf.log', 'w') as f: f.write('iperf server started')
        print("iperf started with pid:", iperf_process.pid)
    except Exception as e:
        print("Error starting iperf:", str(e))

@cli.command()
@click.argument('target', type=str, default="127.0.0.1:7000")
def iperf_client(target):
    try:
        server_ip, port = target.split(":")
        iperf_process = subprocess.Popen(['iperf', '-c', server_ip, '-p', str(port)])
        print("iperf client started with pid:", iperf_process.pid)
    except Exception as e:
        print("Error starting iperf client:", str(e))

if __name__ == '__main__':
    cli()
