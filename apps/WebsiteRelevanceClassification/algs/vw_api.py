#import docker # would've been nice but no docker-compose like functionality
import wabbit_wappa

# Provide access to VWAPI
class VWAPI(object):
    """
    Simple class for defining a set of
    instatiation parameters for vowpal wabbit, access to
    """
    def __init__(self, task='relevance'):
        # both vowpal wabbit relevance and product are initated by the NextML start up process
        # just need to bind a socket here.
        self.DEFAULT_PORT = 7000

        PORT = self.DEFAULT_PORT if task == 'relevance' else 9000 # for product
        # get socket to vowpal wabbit process (stood up by NextML)
        self.vw = wabbit_wappa.VW(daemon_ip='localhost',
                                  active_mode=True,
                                  daemon_mode=True,
                                  port=PORT)

        # should really close the socket on class destruction
        pass

    def get_bulk_responses(self, examples):
        # see: https://github.com/JohnLangford/vowpal_wabbit/wiki/Daemon-example
        # basically, send a newline to delimit each example, vw will respond back similarly

        # First convert raw examples into a vw friendly format...

        # note: this is task and data format specific:
        #       here we assume an array of floats
        vw_examples  = []
        # 8 bytes per float, count prediction, importance, 2 bytes for new
        # line and space between
        max_bytes_per_line = 8+8+2
        num_examples = len(examples)

        for example in examples:
            vw_examples.append(wabbit_wappa.Namespace('default',
                        features = [('col'+str(idx), value)
                                        for idx, value in enumerate(example)]))

        to_send_examples = '\n'.join([self.vw.make_line(namespaces=[f])
                                        for f in vw_examples])

        # get responses ...
        self.vw.vw_process.sock.sendall(to_send_examples)
        raw_responses = self.vw.vw_process.sock.recv(num_examples*max_bytes_per_line+10)# +10 extra just in case
        responses = [wabbit_wapp.VWResult(r, active_mode=True) for r in res.split()]

        assert len(responses) == num_examples,\
            "get_bulk_responses, number recv'ed does not match number examples sent! sent {}, recved {}".format(num_examples, len(responses))
        # can access .prediction or .importance attribute
        return responses
