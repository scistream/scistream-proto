## USAGE: direct connection:
# h2: python pub_bench.py --port 7000 --sync 17000
# h4: python sub_bench.py --remote-host 172.16.1.1 --remote-port 7000 --sync 17000
import time, hashlib, sys, zmq, logging, string, threading, queue
from optparse import OptionParser

logging.basicConfig(level=logging.INFO)


# Parse command line options and dump results
def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option("--port", dest="port", default="50000", help="Publisher TCP port")
    parser.add_option(
        "--sync",
        dest="sync",
        default="51000",
        help="Publisher synchronization TCP port",
    )
    parser.add_option(
        "--size", dest="size", type=int, default=1024, help="Sample size in bytes"
    )
    parser.add_option(
        "--dataset", dest="dataset", type=int, default=10, help="Dataset size in Gbytes"
    )
    parser.add_option(
        "--jitter",
        dest="jitter",
        action="store_true",
        default=False,
        help="Reduce the generation rate to 1 KHz",
    )
    (options, args) = parser.parse_args()

    return options, args


opts, args = parseOptions()
samples = int(opts.dataset * (10**9) / opts.size)

context = zmq.Context()

sync_socket = context.socket(zmq.REP)
sync_socket.bind("tcp://*:%s" % opts.sync)

socket = context.socket(zmq.PUB)
socket.set_hwm(0)
socket.bind("tcp://*:" + opts.port)

logging.info("SYNCing on port %s" % opts.sync)
message = sync_socket.recv_string()
logging.info("Received: %s" % message)
sync_socket.send_string("%s, %s" % (opts.size, samples))
logging.info("SYNCed")

_msg = "SciStream:" + ("a" * opts.size)

logging.info("Starting Publisher...")
next_call = time.time()
for i in range(samples):
    socket.send_string(_msg)
    if not (i % 10):
        logging.debug("Produced sample %s" % i)
    if opts.jitter:
        next_call += 0.001
        sleep_time = next_call - time.time()
        if (
            sleep_time > 0
        ):  # If sleep_time is non-negative, then sleep for the remaining duration
            time.sleep(sleep_time)

socket.send_string(r"SciStream:STOP")
logging.info("Streaming ended, exiting...")

message = sync_socket.recv_string()
logging.info("Received: %s" % message)
sync_socket.send_string("FIN_ACK")
logging.info("Bye, bye...")
sys.exit(0)
