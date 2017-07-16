import numpy as np
#import next.utils as utils
from collections import defaultdict
from vw_api import VWAPI

n= 6
class Butler(object):
    def __init__(self):
        self.algorithms = {}
        self.targets = {}

        self.algorithms.set = lambda(k, v: self.algorithm[k] = v)
        self.targets.get_targetset = lambda(k: self.targets)

butler = Butler()

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
        # Save off (a) and (c) objects from above description, and set answered indices
        butler.algorithms.set(key='n', value=n)
        butler.algorithms.set(key='answered_idxs', value=set())

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

    def get_importances(self, target_examples, update=False):
        print('\t in get importances ...')
        api = VWAPI()

        print('\t getting targets ...')
        #utils.debug_print(str(target_examples))

        # assume target_examples are in perserved index order
        examples = [example['meta']['features'] for example in target_examples]
        print('\t calling my battle heavy get_bulk_responses...')
        answers = api.get_bulk_responses(examples)

        #utils.debug_print(str(answers))

        print('\t closing/shutting down api')
        api.vw.close() # del doesn't seemt to close socket :-/
        del api

        print('\t returning importances, apply np.argsort')
        importances = [answer.importance for answer in answers]
        ordered_importances = np.argsort(importances)

        if update:
            butler.algorithms.set(key='importances', value=ordered_importances)

        # ordered by importance on indices into target_examples
        return ordered_importances

    def get_n_importances(self, butler, n):
        ret = None

        importances = butler.algorithms.get(key='importances')
        answered = butler.algorithms.get(key='answered_idxs')

        filtered_importances = [importance for importance in importances if importance not in answered]

        if filtered_importances:
            ret = filtered_importances[0:n]# returns 0 : length of(importances)
        return ret

    def getQuery(self, butler):
        importances = self.get_n_importances(butler, 5)
        assert len(importances) > 0, 'getQuery: importances list is empty!'

        return np.random.choice(importances, 1)[0]

    def teach(self, butler, target_index, target_label):
        api = VWAPI()

        example = butler.targets.get_target_item(butler.exp_uid, target_index)
        vw_example = api.to_vw_examples([example])

        api.vw.send_example(target_label, features=vw_example)
        api.vw.close()
        del api

    def processAnswer(self, butler, target_index, target_label):
        # Increment the number of reported answers by one.
        num_reported_answers = butler.algorithms.increment(key='num_reported_answers')
        answered = butler.algorithms.append(key='answered_idxs', value=target_index)

        # teach vowpal wabbit
        butler.job('teach', {'target_label':target_label,
                             'target_index':target_index,
                             'butler':butler},
                   time_limit=30)

        # Update importances of examples
        if num_reported_answers % int(3) == 0:
            butler.job('get_importances',
                            {'update':True,
                             'target_examples'=butler.targets.get_targetset(butler.exp_uid)},
                        time_limit=30)

            # should save model here?

        return True

    def getModel(self, butler):
        pass

        # shoudl force save
        # The model is simply the vector of weights and a record of the number of reported answers.
        #utils.debug_print(butler.algorithms.get(key=['weights', 'num_reported_answers']))
        return butler.algorithms.get(key=['weights', 'num_reported_answers'])
