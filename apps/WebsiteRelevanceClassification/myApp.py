import json
import next.utils as utils
import next.apps.SimpleTargetManager
#from vw_api import VWAPIWebsiteRelevance

class MyApp:
    def __init__(self, db):
        self.app_id = 'WebsiteRelevanceClassification'
        self.TargetManager = next.apps.SimpleTargetManager.SimpleTargetManager(db)

    def initExp(self, butler, init_algs, args):
        args['n']  = len(args['targets']['targetset'])

        args['d'] = 2**args['bit_precision']
        args['d'] = len(args['targets']['targetset'][0]['meta']['features'])

        targets = sorted(args['targets']['targetset'],key=lambda x: x['target_id'])
        self.TargetManager.set_targetset(butler.exp_uid, targets)
        del args['targets']

        alg_data = {'n': args['n'],
                    'd': args['d'],
                    'failure_probability': args['failure_probability'],
                    'vw_command_line_arguments': args['vw_command_line_arguments'],
                    'bit_precision': args['bit_precision']}
        init_algs(alg_data)
        return args

    def getQuery(self, butler, alg, args):
        # part 1 of Scott Sivert's suggestion
        importance = butler.algorithms.get(key='importance')

        # given that we only have 300 examples or so it's okay to do a linear search for max I think
        #return max(importance) # return index of max importance.

        alg_response = alg({'participant_uid':args['participant_uid']})
        target = self.TargetManager.get_target_item(butler.exp_uid, alg_response)
        del target['meta']
        return {'target_indices':target}

    def update_importance(butler, answer):
        # part 2 of Scott Sivert's suggestion
        # asynch call to update the importance

        # unclear if should call into algs or call vw directly
        # probably shoudl call into alg since it is called into by the other functions

        #alg({'call vw, get importances'}) ???
        # push targes to vw, on predict(), get answer
        # VW STuff here

        importance = [1]
        butler.algorithms.set(key='importance', value=importance)# array of importances

    def processAnswer(self, butler, alg, args):
        # part 3 of Scott Sivert's suggestion
        butler.job(update_importance, butler, answer) # asynch importance update
        # alg() will call .teach()

        query = butler.queries.get(uid=args['query_uid'])
        target = query['target_indices']
        target_label = args['target_label']

        num_reported_answers = butler.experiment.increment(key='num_reported_answers_for_' + query['alg_label'])

        # importance rank the examples, for easy getQuery selection ~ every n/4 queries

        # make a getModel call ~ every n/4 queries - note that this query will NOT be included in the predict
        experiment = butler.experiment.get()
        d = experiment['args']['d']
        if num_reported_answers % ((d+4)/4) == 0:
            butler.job('getModel', json.dumps({'exp_uid':butler.exp_uid,'args':{'alg_label':query['alg_label'], 'logging':True}}))

        alg({'target_index':target['target_id'],'target_label':target_label})
        return {'target_index':target['target_id'],'target_label':target_label}

    def getModel(self, butler, alg, args):
        return alg()
