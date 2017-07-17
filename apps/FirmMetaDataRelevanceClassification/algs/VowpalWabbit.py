from __future__ import division # so that 1/2 = 0.50, not 0
import numpy as np
import json
import next.utils as utils
import random
from collections import defaultdict
from vw_api import VWAPI
import pymongo

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
        butler.algorithms.set(key='n', value=n) # should this be set at the experiment level?
        butler.algorithms.set(key='answered_idxs', value=[])

        print('\t appear to have successfully set the butler...')
        print('\t attempting to get importances, set importances key')

        # for b, from above description, get importancse and then store them off
        # in ranked importance list

        # note: we block on this call, that's okay beacuse we only init once.
        # future calls should be done asynch
        #importances = self.get_importances(target_examples=butler.targets.get_targetset(butler.exp_uid))
        #butler.algorithms.set(key='importances', value=importances)

        # ... might as well keep track of the number of reported answers for
        # overall tracking purposes. Might be more appropriate in MyApp.py
        butler.algorithms.set(key='num_reported_answers', value=0)

        #imps = butler.algorithms.get(key='importances')
        #print('\t *** imps: ', len(imps))
        #imps = butler.algorithms.get(key='n')
        #print('\t *** n: ', imps)
        #imps = butler.algorithms.get(key='num_reported_answers')
        #print('\t *** num_reported_answers: ', imps)

        return True

    def train_learner(self):
        """
        As a simple way to maintain learner state we simply pass all
        prior non-held out examples to it to train it (learners start up untrained)

        This puts the storage onto NextML, in the database and avoides the need to
        version and other save save off different learners.

        If you want to train a unique learner simple use the NextML API to retrieve
        the examples and transform them however is desired.
        """

        # could read out of butler.memory (stsievert) or butler.application
        pass

    def get_importances(self, butler=None, target_examples=None, update=False):
        print('\t in get importances ...')
        api = VWAPI() # TODO: use VW_METADATA, port=10000

        print('\t getting targets ...')

        # assume target_examples are in perserved index order
        examples = [example['meta']['features'] for example in target_examples]
        answers = api.get_bulk_responses(examples)

        print('\t closing/shutting down api')
        api.vw.close() # del doesn't seemt to close socket :-/
        del api

        importances = [answer.importance for answer in answers]
        ordered_importances = np.argsort(importances)

        if update:
            butler.algorithms.set(key='importances', value=ordered_importances)

        # ordered by importance on indices into target_examples
        return ordered_importances

    def get_n_importances(self, butler, n):
        ret = None

        importances = butler.algorithms.get(key='importances')
        answered = set()
        if butler.algorithms.get(key='answered_idxs'):
            answered = set(butler.algorithms.get(key='answered_idxs'))

        filtered_importances = [importance for importance in importances if importance not in answered]

        if filtered_importances:
            ret = filtered_importances[0:n]# returns 0 : length of(importances)
        return ret

    def getQuery(self, butler, participant_uid):
        return True

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
        #print(args)
        args = json.loads(args)
        target_label = args['args']['target_label']
        example = args['args']['example']

        print('\t*** about to teach ...')
        api = VWAPI(task='metadata', host='localhost', port=10000)

        # products are represented as a bag of words (and maybe syntax too)
        vw_example = api.to_vw_examples([example])

        #print("\t*** vw_example: ", str(vw_example))

        api.vw.add_namespaces(vw_example)

        # important to send namespaces, not features, because
        # to_vw_examples creates namespaces
        api.vw.send_example(response=target_label)
        api.vw.close()
        del api

        print('\t*** ... taught')

    def processAnswer(self, butler, target_index, target_label):

        return True

        # TODO: fix up to teach and/or do hold out, given below

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

        # Create hold out set for accuracy evaluation
        if (num_reported_answers % 4) == 0:
            print('\t **** We held out an example, yay!')
            butler.experiment.append(key='hold_out', value=(target_index, target_label))
            k = butler.experiment.get(key='hold_out')
            print k, ' ... is our hold out set'
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

        # If target_label is positive then we remove from the mongodb database
        # ... using butler.job bcause we're not sure how long it'll take to connec to db and remove from it
        if target_label == -1: # a positive label (see getquery_widget.html page)
            print('\t ... going to remove this instance from the data base')
            butler.job('remove_metadata',
                       json.dumps({'args': {'target_index':target_index}}),
                       time_limit=600)

        return True

    def remove_metadata(self, butler, args):
        business_name = butler.targets.get_target_item(butler.exp_uid, target_index)['business_name']
        region = butler.targets.get_target_item(butler.exp_uid, target_index)['region']

        # get cursor to db, get collection, delete given (business, region) from new database
        # so it's no longer served
        client = pymong.MongoClient()# connects to metadata firm webapp db
        db = client['flaskr'] # this should be in the api, as a constant
        collection = db['new_business_region']
        result = collection.delete_many({'business_name': business_name,
                                         'region': region})

        # Also need to mark submitted data with label
        collection = db['submitted_business_region']
        doc = collection.find_one({'business_name': business_name,
                               'region': region})
        if doc is not None:
            doc['verified'] = True
            collection.save(doc)

        # so now an outside process can continiously pull for verified=True documents in the
        # submitted collection and join them to product and website names, yay!

        # This outside process is essentially Stage 5


    def getModel(self, butler):
        precision = random.random()

        num_reported_answers = butler.experiment.get(key='num_reported_answers')

        butler.algorithms.set(key='precision', value=precision)
        ret = butler.algorithms.get(key=['precision', 'num_reported_answers'])
        #print ret

        num_reported_answers = ret['num_reported_answers'] # to prove that we can make it non None
        print('num reported', num_reported_answers, '<')
        print type(num_reported_answers), type(precision)

        # Debug area for getting hold out accuracy
        hold_out = None
        if butler.experiment.get(key='hold_out'):
            hold_out = set(butler.experiment.get(key='hold_out'))
        print('\t ***', hold_out, ' is hold out')

        if hold_out: # during inital queries it can be null beause nothing was held out
            print('\t *** len of hold out: ', len(hold_out)) # have length

            # so here we have a hold out and we need to test with it
            hold_out_features = [butler.targets.get_target_item(butler.exp_uid, value[0])['meta']['features']\
                                    for value in hold_out]

            print(len(hold_out_features))

            api = VWAPI(task='metadata', host='localhost', port=10000)

            answers = api.get_bulk_responses(hold_out_features)
            api.vw.close() # del doesn't seemt to close socket :-/
            del api

            # Here we compare signs for the predicted answer and the held example
            # a cheap way to threshold the linear regression to a categorical variable
            scores = [(answer.prediction < 0) == (held_out_example[1] < 0) for answer, held_out_example in zip(answers, hold_out)]
            precision = sum(scores)/len(scores)

            print(scores, precision)

        # this return is identical to get()
        #return butler.algorithms.get(key=['precision', 'num_reported_answers'])
        return {'precision':precision,
                'num_reported_answers': num_reported_answers}
