# Usage appcontroller.py uid_value PROD localhost:5000
import click
import grpc
import zmq
import subprocess
import os
import signal
import time
import socket
import sys
from proto import scistream_pb2
from proto import scistream_pb2_grpc

class AppCtrl():
    def __init__(self, uid, role, s2cs, access_token):
        ## Maybe be a scistream notifier
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
            metadata = (
                ('authorization', f'{access_token}'),
            )
            print("AppCtrl: SENDING HELLO")
            try:
                self.response = s2cs.hello(request, metadata=metadata)
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.UNAUTHENTICATED:
                    sys.exit(f"AppCtrl: Authentication error for server scope, please obtain new credentials: {e.details()}")
                else:
                    sys.exit(f"AppCtrl: Another GRPC error occurred: {e.details()}")
            print("AppCtrl: Hello sent")

        self.start_app(role)

    def kill_python_processes_on_port(self, port):
        try:
            result = subprocess.check_output(f"lsof -i :{port} -n | grep LISTEN | grep python | awk '{{print $2}}'", shell=True)
            pid = int(result.decode("utf-8").strip())
            os.kill(pid, signal.SIGKILL)
        except ValueError:
            print(f"No python process listening on port {port}")
        except subprocess.CalledProcessError:
            print(f"No python process listening on port {port}")
        except ProcessLookupError:
            print(f"Process with PID {pid} not found")

    def start_app(self, role):
        if role == "PROD":
            self.kill_python_processes_on_port("7000")
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

def check_if_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost',int(port))) == 0

@cli.command()
@click.argument('port', type=str, default="7000")
def iperf_server(port):
    if not check_if_port_in_use(port):
        with open('server_output.txt', 'w') as f:
            subprocess.Popen(
                ["iperf", "-s", "-p", str(port)],
                stdout=f,
                stderr=subprocess.STDOUT)    
        print(f"Started iperf server on port {port}")
    else:
        print(f"Port {port} is already in use")

@cli.command()
@click.argument('target', type=str, default="127.0.0.1:7000")
def iperf_client(target):
    try:
        server_ip, port = target.split(":")
        print("STARTING IPERF CLIENT with port:", str(port))
        with open('client_output.txt', 'w') as f:
            iperf_process = subprocess.Popen(
                ['iperf', '-t', '10', '-c', server_ip, '-p', str(port)],
                stdout = f,
                stderr = subprocess.STDOUT)
        print("iperf client started with pid:", iperf_process.pid)
    except Exception as e:
        print("Error starting iperf client:", str(e))

if __name__ == '__main__':
    cli()
