import json
import random
import next.utils as utils
import next.apps.SimpleTargetManager

class MyApp:
    """
    The Product and WebsiteRelevance apps are used as oracles to filter instances,
    however, the Firm Metadat app is primarily used to directly query MTurk and
    confirm submitted information, not to filter instances.

    This means that this App is a bit simpler in how it selects the next query:
        just return the next submitted business that it has not verified.

    As a side effect, we also train the Oracle but we do nothing with it.

    One migth ask, why bother with the oracle then? NextML provides a very convienent
    framework to expose to MTurk and collect answers. Additionally, having a
    human in the loop trained Metadata verifier, if accurate enough down the road,
    woudl cut the cost of the Metadata stage by about half, which is worth striving for.

    Summary: This app basically returns the next unverified business metadata and uses
    the answer to teach an oracle that isn't really used w/in context of the system as of yet.
    """
    def __init__(self, db):
        self.app_id = 'FirmMetaDataRelevanceClassification'
        self.TargetManager = next.apps.SimpleTargetManager.SimpleTargetManager(db)

    def initExp(self, butler, init_algs, args):
        """
        initExp

        Get the number of examples, very short function. Set up current idx
        into the targetset for getQuery calls, etc.
        """

        # set up targets as is
        args['n']  = len(args['targets']['targetset'])
        self.TargetManager.set_targetset(butler.exp_uid,
                                         args['targets']['targetset'])

        print('\t idx is ', args['idx'])
        #args['idx'] = args['idx'] # offset to fetch target example at
        #butler.experiment.set(key='idx', value=0)

        alg_data = {'n': args['n']}

        init_algs(alg_data)

        return args

    def getQuery(self, butler, alg, args):
        """
        Return the next unverified submitted business metadata item.

        Wraps around to 0 if none are left
        """
        participant_uid = args.get('participant_uid', butler.exp_uid)
        alg({'participant_uid':participant_uid}) # seems to populate log_entry_duration, even though it's a stub

        idx = butler.experiment.get(key='args')['idx']
        n = butler.experiment.get(key='args')['n']
        print('\t in getQuer, idx is ', idx)

        target = self.TargetManager.get_target_item(butler.exp_uid, idx)
        butler.experiment.set(key='idx', value= (idx + 1) % n)
        print('target: ', target)

        return {'target_indices':target}

        targets_list = [{'target':target}]

        return_dict = {'target_indices':targets_list}
        experiment_dict = butler.experiment.get()
        if 'labels' in experiment_dict['args']['rating_scale']:
            labels = experiment_dict['args']['rating_scale']['labels']
            return_dict.update({'labels':labels})

        if 'context' in experiment_dict['args'] and 'context_type' in experiment_dict['args']:
            return_dict.update({'context':experiment_dict['args']['context'],'context_type':experiment_dict['args']['context_type']})

        return return_dict




    def processAnswer(self, butler, alg, args):
        query = butler.queries.get(uid=args['query_uid'])
        target = query['target_indices']
        target_label = args['target_label']

        num_reported_answers = butler.experiment.increment(key='num_reported_answers_for_' + query['alg_label'])

        print(query)

        # TODO: call teach on VW
        # every so often call getModel as below so that we can see how its doing


        ##print(' target', target, 'target_label: ', target_label)
        #experiment = butler.experiment.get()
        #if (num_reported_answers % 2) == 0:
        #    butler.job('getModel', json.dumps({'exp_uid':butler.exp_uid,'args':{'alg_label':query['alg_label'], 'logging':True}}))

        #alg({'target_index':target['target_id'],'target_label':target_label})
        return {'target_index':target['target_id'],'target_label':target_label}

    def getModel(self, butler, alg, args):
        # pass to getModel I guess?
        return alg()
