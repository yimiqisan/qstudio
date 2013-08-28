# -*- coding:utf-8 -*-

import os
import time
import unittest

from flexmock import flexmock

from guokr.platform.services import search

class SEARCHTestCase(unittest.TestCase):

    def setUp(self):
        os.environ['GUOKR_ELASTICSEARCH_DOMAIN'] = '10.0.80.8:9200'
        os.environ['GUOKR_APPNAME'] = 'guokrplustest'

    def tearDown(self):
        pass

    def test_search(self):
        mock = flexmock(search)
        mock.should_receive('index').once()
        mock.should_receive('get').and_return({'_source': {'test': 'haha'}}).and_return({'_source': {'test': 'hehe'}}).and_return({'exists': False})
        mock.should_receive('update').once()
        mock.should_receive('search').and_return({'hits': {'hits': [{'_id': 'id1'}]}}).once()
        mock.should_receive('delete').once()
        search.index('type1', 'id1', {'test': 'haha'})
        ret = search.get('type1', 'id1')
        self.assertEqual(ret['_source']['test'], 'haha')
        search.update('type1', 'id1', {'test': 'hehe'})
        ret = search.get('type1', 'id1')
        self.assertEqual(ret['_source']['test'], 'hehe')
        #time.sleep(1)
        ret = search.search('hehe')
        self.assertEqual(ret['hits']['hits'][0]['_id'], 'id1')
        search.delete('type1', 'id1')
        ret = search.get('type1', 'id1')
        self.assertEqual(ret['exists'], False)

    def test_advanced_search(self):
        mock = flexmock(search)
        mock.should_receive('index').twice()
        search.index('type1', 'id2', {'test': 'haha'})
        search.index('type2', 'id3', {'test': 'haha'})
        #time.sleep(1)
        ES = search.get_esclient_instance()
        terms = {'query_string': {'fields': ['test'], 'query': 'haha'}}
        q = {'query': terms, 'from': 0, 'size': 10}
        mock = flexmock(ES)
        mock.should_receive('search').and_return({'hits': {'hits': [{'_id': 'id2'}, {'_id': 'id3'}]}}).once()
        ret = ES.search(q, indexes=[search.get_base_index()], doctypes=['type1', 'type2'])
        self.assertEqual(len(ret['hits']['hits']), 2)

    def test_batch_search(self):
        with search.index_pipeline() as pipe:
            mock = flexmock(pipe)
            mock.should_receive('index').twice()
            pipe.index('type3', 'id3', {'test': 'haha'})
            pipe.index('type3', 'id5', {'test': 'haha'})
        with search.index_pipeline() as pipe:
            mock = flexmock(pipe)
            mock.should_receive('index').once()
            mock.should_receive('delete').once()
            pipe.index('type3', 'id4', {'test': 'haha'})
            pipe.delete('type3', 'id5')
        with search.get_pipeline() as pipe:
            mock = flexmock(pipe)
            mock.should_receive('get').twice()
            mock.should_receive('execute').and_return({'docs': [{'_id': 'id4'}, {'_id': 'id5'}]})
            pipe.get('type3', 'id3')
            pipe.get('type3', 'id4')
            ret = pipe.execute()
        self.assertEqual(len(ret['docs']), 2)
        #time.sleep(1)
        with search.search_pipeline() as pipe:
            mock = flexmock(pipe)
            mock.should_receive('search').once()
            mock.should_receive('execute').and_return({'responses': [{'hits': {'total': 2}}]})
            pipe.search('haha')
            ret = pipe.execute()
        self.assertEqual(ret['responses'][0]['hits']['total'], 2)
        ES = search.get_esclient_instance()
        terms = {'query_string': {'fields': ['test'], 'query': 'haha'}}
        q = {'query': terms, 'from': 0, 'size': 10}
        with ES.pipeline('msearch') as pipe:
            mock = flexmock(pipe)
            mock.should_receive('search').once()
            mock.should_receive('execute').and_return({'responses': [{'hits': {'total': 2}}]})
            pipe.search(q, indexes=[search.get_base_index()], doctypes=['type3'])
            ret = pipe.execute()
        self.assertEqual(ret['responses'][0]['hits']['total'], 2)

if __name__ == '__main__':
    unittest.main()
