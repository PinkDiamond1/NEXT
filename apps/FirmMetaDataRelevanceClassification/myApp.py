import json
import random
import next.utils as utils
import next.apps.SimpleTargetManager

class MyApp:
    def __init__(self, db):
        self.app_id = 'FirmMetaDataRelevanceClassification'
        self.TargetManager = next.apps.SimpleTargetManager.SimpleTargetManager(db)

    def initExp(self, butler, init_algs, args):
        """
        initExp

        Push examples to the TargetManager, pass examples to alg for importance order
        sorting for follow on getQuery, processAnswer calls.

        This function is pretty
        light because the underlying algorithm requires no parameters (due to
        it already be started up by nextml, defined in next/vowpal_wabbit_image/*.yaml
        """

        # set up targets as is
        args['n']  = len(args['targets']['targetset'])
        self.TargetManager.set_targetset(butler.exp_uid,
                                         args['targets']['targetset'])

        alg_data = {'n': args['n']}

        # allow the algorithm to create a importance ranked list of the targets
        init_algs(alg_data)
        return args

    def getQuery(self, butler, alg, args):
        alg_response = alg({'participant_uid':args['participant_uid']})
        target = self.TargetManager.get_target_item(butler.exp_uid, alg_response)
        del target['meta']
        return {'target_indices':target}

    def processAnswer(self, butler, alg, args):
        query = butler.queries.get(uid=args['query_uid'])
        target = query['target_indices']
        target_label = args['target_label']

        num_reported_answers = butler.experiment.increment(key='num_reported_answers_for_' + query['alg_label'])

        print(query)
        #print(' target', target, 'target_label: ', target_label)
        experiment = butler.experiment.get()
        if (num_reported_answers % 2) == 0:
            # artifically set log_entry_durations, better set via WRC/myApp.yaml
            butler.job('getModel', json.dumps({'exp_uid':butler.exp_uid,'args':{'alg_label':query['alg_label'], 'logging':True}}))

        alg({'target_index':target['target_id'],'target_label':target_label})
        return {'target_index':target['target_id'],'target_label':target_label}

    def getModel(self, butler, alg, args):
        return alg()
