import json
import random
import next.utils as utils
import next.apps.SimpleTargetManager
import pymongo

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
        # args['idx'] is also accessible
        self.TargetManager.set_targetset(butler.exp_uid,
                                         args['targets']['targetset'])

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

        target = self.TargetManager.get_target_item(butler.exp_uid, idx)
        print('target: ', target)

        return {'target_indices':target}


    def processAnswer(self, butler, alg, args):
        query = butler.queries.get(uid=args['query_uid'])
        target = query['target_indices']
        target_label = args['target_label']

        n = butler.experiment.get(key='args')['n']
        num_reported_answers = butler.experiment.increment(key='num_reported_answers_for_' + query['alg_label'])

        # Handle answer...

        # First we remove from new business region collection if verified correct so that
        # we don't serve it up again
        client = pymongo.MongoClient(host="flask_app", port=30000)
        db = client['flaskr_db']
        if target_label == -1: # -1 indicates was verified correctly (see query widget on -1/1 label assignment)
            print('\t would have delete many off of target', target)
            print('\t ... role', target[u'role'])
            print('\t ... yeah...')
            # There is, unfortunately, a one to many (3 to be exact) relationship between new business regions and
            # the NextML submitted business region format, where NextML has a row for each role typ (CEO, manager, employee)
            #
            # What this means is that we may delete an item from new business just off of the sucess
            # of one role. However, if we come across an incorrectly submitted role we must re add that
            # to the webapp database.
            #ret = db['new_business_region'].delete_many({'business_name':target['business_name'],
            #                                             'region':target['region']})
            for doc in db['new_business_region'].find():
                print(doc)
            print({'business_name':target['business_name'], 'region':target['region']})
            print('ret is ', ret)

            # ... now we also need to indcate in submitted business region that this is correct
            #db = client['submitted_business_region']
            #db.update_one({'business_name':target['business_name'],
            #                'region':target['region'],
            #                'role': target['role']},
            #                 {'$set':{'verified':True}}

            # then add in vw to right port,
            # then add in tokenized web data
        # else we leave it in the new business region for another turker to correctly identify information for

        #if target_label == 1: # data is not on the role, business region :(
        # re-add to new business region

        if num_reported_answers >= n:
            # experiment is over because all submitted business have been verified as correct
            raise Exception, "Experiment is over; all submitted businesses in experiment are correct!"



        print(query)

        # TODO: call teach on VW
        # every so often call getModel as below so that we can see how its doing


        ##print(' target', target, 'target_label: ', target_label)
        #experiment = butler.experiment.get()
        #if (num_reported_answers % 2) == 0:
        #    butler.job('getModel', json.dumps({'exp_uid':butler.exp_uid,'args':{'alg_label':query['alg_label'], 'logging':True}}))

        alg({'target_index':target['target_id'],'target_label':target_label})
        return {'target_index':target['target_id'],'target_label':target_label}

    def getModel(self, butler, alg, args):
        # pass to getModel I guess?
        return alg()
