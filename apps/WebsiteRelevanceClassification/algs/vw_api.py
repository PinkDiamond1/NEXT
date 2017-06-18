#import docker # would've been nice but no docker-compose like functionality
import wabbit_wrappa

# Provide access to VWAPI
class VWAPI(object):
    """
    Simple class for defining a set of
    instatiation parameters for vowpal wabbit, access to
    """
    PORT = 7000
    def __init__(self, task='relevance'):
        # both vowpal wabbit relevance and product are initated by the NextML start up process
        # just need to bind a socket here.

        PORT = PORT if task == 'relevance' else 9000 # for product
        # get socket to vowpal wabbit process (stood up by NextML)
        self.vw = wabbit_wappa.VW(daemon_ip='localhost',
                                  active_mode=True,
                                  daemon_mode=True,
                                  port=PORT)

        # should really close the socket on class destruction
        pass

    def get_bulk_importances(self, examples, predictions=False):
        # see: https://github.com/JohnLangford/vowpal_wabbit/wiki/Daemon-example
        # basically, send a return to delimit each example, vw will respond back similarly

        # may need to unpack examples/answers at the api side
        ret = None
        responses = self.vw.get_prediction(examples)# can wabbit wappa get bulk predictions?

        importance_responses = responses.importance # can wabbit wappa return bulk importances?
        if predictions:
            prediction_responses = responses.prediction

        ret = (importance_responses, prediction_responses) if predictions else importance_responses

        return ret

    def get_bulk_predictions(self, examples):
        return self.get_importance(examples, predictions=True)
