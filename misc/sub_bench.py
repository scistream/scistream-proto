import time, zmq, sys
import logging
import statistics
from threading import Thread
from optparse import OptionParser

logging.basicConfig(level=logging.INFO)


# Parse command line options and dump results
def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option(
        "--remote-host", dest="host", default="127.0.0.1", help="Remote host IP address"
    )
    parser.add_option(
        "--remote-port", dest="port", default="50000", help="Remote TCP port"
    )
    parser.add_option(
        "--sync", dest="sync", default="51000", help="Synchronization TCP port"
    )
    parser.add_option(
        "--log-file", dest="fname", default="streaming_res.log", help="Log file name"
    )
    parser.add_option(
        "--pacing",
        dest="pacing",
        action="store_false",
        default=False,
        help="Reduce the consumption rate",
    )
    parser.add_option(
        "--st", dest="st", type=float, default=0.001, help="Sampling time"
    )
    (options, args) = parser.parse_args()

    return options, args


class Poller(Thread):
    def __init__(self, id, topic):
        super().__init__()
        self.id = id
        self.topic = topic

    def run(self):
        opts, args = parseOptions()
        # Initialize log files
        results_log = open(opts.fname, "a+")

        context = zmq.Context()

        sync_socket = context.socket(zmq.REQ)
        sync_socket.connect("tcp://" + opts.host + ":" + opts.sync)

        subscriber = context.socket(zmq.SUB)
        subscriber.set_hwm(0)
        subscriber.connect("tcp://" + opts.host + ":" + opts.port)
        subscriber.setsockopt_string(zmq.SUBSCRIBE, self.topic)

        logging.info("SYNCing with Publisher...")
        sync_socket.send_string("SYNC")
        resp = sync_socket.recv_string()
        size = resp.split(",")[0]
        samples = resp.split(",")[1]
        logging.info("Expecting %s samples of %s bytes" % (samples, size))

        logging.info("start poller {} with topic {}".format(self.id, self.topic))

        count = 0
        self.start = time.time()
        inter_msg_space = []
        while True:
            # message = subscriber.recv_string()
            message = subscriber.recv()
            now = time.time()
            if not (count % 10):
                logging.debug(
                    "{}: MSG {} @ local time {}".format(
                        count, message[:11], time.strftime("%H:%M:%S")
                    )
                )
            # if message == b'SciStream:STOP':
            if message.decode("utf-8")[10] == "S":
                t = t_last_msg - self.start
                throughput = (8 * float(size) * count) / ((10**9) * t)
                efficiency = 100 * count / float(samples)
                avg_ims = statistics.mean(inter_msg_space)
                jitter = statistics.stdev(inter_msg_space)
                logging.info(
                    "Elapsed: %s secs. | Throughput: %.3f Gbps | Jitter: %f | Inter-message Space: %f | Efficiency: %.2f%%"
                    % (t, throughput, jitter, avg_ims, efficiency)
                )
                results_log.write(
                    "%s,%s,%s,%s\n" % (throughput, jitter, avg_ims, efficiency)
                )
                results_log.flush()
                results_log.close()
                sync_socket.send_string("FIN")
                resp = sync_socket.recv_string()
                logging.info("Received reply: %s" % resp)
                break
            else:
                if count > 0:
                    inter_msg_space.append(now - t_last_msg)
                    t_last_msg = now
                else:
                    t_last_msg = now
                count += 1
                if opts.pacing:
                    time.sleep(opts.st)


if __name__ == "__main__":
    poller1 = Poller(1, "SciStream")
    poller1.start()

    sys.exit(0)
