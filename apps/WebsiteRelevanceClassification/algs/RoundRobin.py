import numpy as np
import json
import next.utils as utils
import random
from collections import defaultdict
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

    def get_importances(self, butler=None, target_examples=None, update=False):
        print('\t in get importances ...')
        api = VWAPI()

        print('\t getting targets ...')
        utils.debug_print(str(target_examples))

        # assume target_examples are in perserved index order
        examples = [example['meta']['features'] for example in target_examples]
        #print('\t calling my battle heavy get_bulk_responses...')
        answers = api.get_bulk_responses(examples)

        utils.debug_print(str(answers))

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

    def getQuery(self, butler, participant_uid):
        importances = self.get_n_importances(butler, 5)
        assert len(importances) > 0, 'getQuery: importances list is empty!'

        return np.random.choice(importances, 1)[0]

    def call_get_importances(self, butler, args=None):
        # proxy function to call get_importances since job signatures are different
        if args:
            args = json.loads(args)
            target_examples = args['args']['target_examples']
            update = args['args']['update']

        self.get_importances(target_examples=target_examples,
                             butler=butler,
                             update=update)


    def teach(self, butler, args):
        print(args)
        args = json.loads(args)
        target_label = args['args']['target_label']
        example = args['args']['example']

        print('\t*** about to teach ...')
        api = VWAPI()

        vw_example = api.to_vw_examples([example])

        print("\t*** vw_example: ", str(vw_example))

        api.vw.add_namespaces(vw_example)

        # important to send namespaces, not features, because
        # to_vw_examples creates namespaces
        api.vw.send_example(response=target_label)
        api.vw.close()
        del api

        print('\t*** ... taught')

    def processAnswer(self, butler, target_index, target_label):
        # S maintains a list of labelled items. Appending to S will create it.
        butler.algorithms.append(key='S', value=(target_index, target_label))

        # Increment the number of reported answers by one.
        num_reported_answers = butler.algorithms.increment(key='num_reported_answers')
        answered = butler.algorithms.append(key='answered_idxs', value=target_index) # redundant

        print('\t*** num answers: ', num_reported_answers, '\t answered ', str(answered))
        print('\t*** target index: ', target_index, '\n\t\t target_label ', str(target_label))

        # teach vowpal wabbit
        example = butler.targets.get_target_item(butler.exp_uid, target_index)['meta']['features']

        #print('\t *** is example: ',  example)

        # Debug

        # Create hold out set for accuracy evaluation
        if (num_reported_answers % 4) == 0:
            print('\t **** We held out an example, yay!')
            butler.algorithms.append(key='hold_out', value=(target_index, target_label))
        else: # store off hold out example for proper evaluation testing

            print('\t*** about to teach vowpal wabbit with this one answer')
            butler.job('teach',
                       json.dumps({'args':
                                    {'target_label':target_label,
                                     'example':example}
                                  }),
                       time_limit=30)

        # Update Active Learning sampling ranking
        # Update importances of examples, use call_* for different signature
        if num_reported_answers % int(3) == 0:
            print('\t about to get new imortances')
            butler.job('call_get_importances',
                       json.dumps({'args':
                                       {'update':True,
                                        'target_examples':butler.targets.get_targetset(butler.exp_uid)}
                                   }),
                       time_limit=30)

            #butler.job('getModel', {}, time_limit=30)

        return True

    def getModel(self, butler):
        alg_label = "RoundRobin"#args['alg_label']
        mock_precision = random.random()

        # ?nextml bug, this returns None even though get the same call works in processAnswer above
        num_reported_answers = butler.experiment.get(key='num_reported_answers')

        butler.algorithms.set(key='mock_precision', value=mock_precision)
        ret = butler.algorithms.get(key=['mock_precision', 'num_reported_answers'])
        print ret

        print('num reported', num_reported_answers, '<')
        print type(num_reported_answers), type(mock_precision)

        num_reported_answers = ret['num_reported_answers'] # to prove that we can make it non None
        print('num reported', num_reported_answers, '<')
        print type(num_reported_answers), type(mock_precision)

        # Debug area for getting hold out accuracy
        hold_out = butler.algorithms.get(key='hold_out')
        if hold_out: # during inital queries it can be null beause nothing was held out
            print('\t *** len of hold out: ', len(hold_out)) # have length
            #print(hold_out[-1]) # make sure we have something here... have


        # this return is identical to get()
        #return butler.algorithms.get(key=['mock_precision', 'num_reported_answers'])
        return {'mock_precision':mock_precision,
                'num_reported_answers': num_reported_answers}
