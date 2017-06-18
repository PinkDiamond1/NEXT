#import docker # would've been nice but no docker-compose like functionality
import wabbit_wrappa

# Provide access to VWAPI
class VWAPI(object):
    """
    Simple class for defining a set of
    instatiation parameters for vowpal wabbit, access to
    """
    PORT = 7000
    def __init__(self):
        # both vowpal wabbit relevance and product are initated by the NextML start up process
        # just need to bind a socket here.
        pass

