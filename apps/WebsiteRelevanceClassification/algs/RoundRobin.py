import numpy as np
import next.utils as utils
from collections import defaultdict
# note on VWAPI
# We are to instantiate it and delete it when we're done
# it actually connects a socket to the the VW docker container and
# the socket isn't easily marshalled or shared so it's better to tear it
# down when done. We only use VWAPI every so often to update key alg data
# so its use is amortized over time.
from vw_api import VWAPI

class MyAlg:
    def initExp(self, butler, n):
        """
        MyAlg.initExp

        Given n, number of examples, access to the butler object, we
        a) set n as the number of examples
        b) create a new object, importances, which is sorted list of
        targetset indices in importance ranked order (most important first)
        c) create a record of what examples have been answered and how
        """

        # get visible logging first
        # this really does not seem to work :(
        #butler.log('DebugLog', "I'm inside MyAlg")# does not appear to log

        assert n != None, "\t alg, initExp: value n is None!"
        # Save off (a) and (c) objects from above description
        butler.algorithms.set(key='n', value=n)
        butler.algorithms.set(key='answered_targets', value = defaultdict(list))

        print('\t appear to have successfully set the butler...')
        print('\t attempting to get importances, set importances key')

        # for b, from above description, get importancse and then store them off
        # in ranked importance list

        # note: we block on this call, that's okay beacuse we only init once.
        # future calls should be done asynch
        importances = self.get_importances(target_examples=butler.targets.get_targetset(butler.exp_uid))
        butler.algorithms.set(key='importances', value=importances)

        # ... might as well keep track of the number of reported answers for
        # overall tracking purposes. Might be more appropriate in MyApp.py
        butler.algorithms.set(key='num_reported_answers', value=0)
        return True

    def get_importances(self, target_examples):
        print('\t in get importabces ...')
        api = VWAPI()

        print('\t getting targets ...')
        utils.debug_print(str(target_examples))

        examples = [example['meta']['features'] for example in target_examples]
        print('\t calling my battle heavy get_bulk_responses...')
        answers = api.get_bulk_responses(examples)

        utils.debug_print(str(answers))

        print('\t closing/shutting down api')
        api.vw.close() # del doesn't seemt to close socket :-/
        del api

        raise NotImplementedError, 'Stopping riiiiight here'

        print('\t returning importances, apply np.argsort')
        print(np.argsort, importances)
        importances = [answer.importance for answer in answers]
        return np.argsort(importances) # ordered by importance on indices into target_examples

    def getQuery(self, butler, participant_uid):
        # Retrieve the number of targets and return the index of the one that has been sampled least
        idx = butler.algorithms.get(key='target_index')
        n = butler.algorithms.get(key='n')
        butler.algorithms.set(key='target_index', value=(idx+1) % n)

        return idx

    def processAnswer(self, butler, target_index, target_label):
        # S maintains a list of labelled items. Appending to S will create it.
        butler.algorithms.append(key='S', value=(target_index, target_label))
        # Increment the number of reported answers by one.
        num_reported_answers = butler.algorithms.increment(key='num_reported_answers')

        # Run a model update job after every d answers
        d = butler.algorithms.get(key='d')
        if num_reported_answers % int(d) == 0:
            butler.job('full_embedding_update', {}, time_limit=30)
        return True

    def getModel(self, butler):
        # The model is simply the vector of weights and a record of the number of reported answers.
        utils.debug_print(butler.algorithms.get(key=['weights', 'num_reported_answers']))
        return butler.algorithms.get(key=['weights', 'num_reported_answers'])

    def full_embedding_update(self, butler, args):
        # Main function to update the model.
        labelled_items = butler.algorithms.get(key='S')
        # Get the list of targets.
        targets = butler.targets.get_targetset(butler.exp_uid)
        # Extract the features form each target and then append a bias feature.
        target_features = [targets[i]['meta']['features'] for i in range(len(targets))]
        for feature_vector in target_features:
            feature_vector.append(1.)
        # Build a list of feature vectors and associated labels.
        X = []
        y = []
        for index, label in labelled_items:
            X.append(target_features[index])
            y.append(label)
        # Convert to numpy arrays and use lstsquares to find the weights.
        X = np.array(X)
        y = np.array(y)
        weights = np.linalg.lstsq(X, y)[0]
        # Save the weights under the key weights.
        butler.algorithms.set(key='weights', value=weights.tolist())
