# -*- coding:utf-8 -*-

import os
import unittest
from requests import Response

from flexmock import flexmock
from frame.platform import urlfetch
from frame.platform.services import taskqueue
from frame.platform.flask import Flask

class TQTestCase(unittest.TestCase):

    def setUp(self):
        os.environ['STUDIO_SERVER_SERVICES'] = 'services.dev.guokr.com'
        os.environ['STUDIO_SERVER_BACKENDS'] = 'backends.dev.guokr.com'
        os.environ['STUDIO_SERVER_APIS'] = 'apis.dev.guokr.com'
        os.environ['STUDIO_APPNAME'] = 'test'
        self.app = app = Flask('test')
        app.config['SERVER_NAME'] = 'dev.guokr.com'
        urlfetch.session()

        @app.route('/test.<_format>', subdomain='backends')
        def test_view():
            pass

    def test_outside_app(self):
        resp = Response()
        resp.status_code = 200
        resp._content = '{"ok": true}'

        flexmock(urlfetch.S).should_receive('request').with_args(
        method='POST',
        url='http://services.dev.guokr.com/taskqueue.json',
        files=None,
        data={
            'appname': 'test',
            'method_': 'GET',
            'url_': 'http://www.g.cn',
            'countdown_': 0
            }).and_return(resp).once()
        taskqueue.add_url('http://www.g.cn') # success

        flexmock(urlfetch.S).should_receive('request').and_return(resp)
        self.assertRaises(RuntimeError, taskqueue.add_url, '/test') # fail
        self.assertRaises(RuntimeError, taskqueue.add, '.test_view') # fail

        with self.app.test_request_context('http://localhost/testxx'):
            flexmock(urlfetch.S).should_receive('request').with_args(
                method='POST',
                url='http://services.dev.guokr.com/taskqueue.json',
                files=None,
                data={
                    'appname': 'test',
                    'method_': 'POST',
                    'url_': 'http://backends.dev.guokr.com/test.json',
                    'countdown_': 0
                }).and_return(resp).twice()
            taskqueue.add_url('/test.json', method_='POST') # success
            taskqueue.add('.test_view', method='POST') # success

    def test_shortcuts(self):
        from frame.platform.apis import fakeapp
        resp = Response()
        resp.status_code = 200
        resp._content = '{"ok": true}'

        flexmock(urlfetch.S).should_receive('request').with_args(
        method='POST',
        url='http://services.dev.guokr.com/taskqueue.json',
        files=None,
        data={
            'appname': 'test',
            'method_': 'PUT',
            'url_': 'http://apis.dev.guokr.com/fakeapp/fake_res.json',
            'countdown_': 30,
            'data1': 123,
            'data2': 'abc',
            }).and_return(resp).once()

        fakeapp.fake_res.update(data1=123, data2='abc', _delay=30)

if __name__ == '__main__':
    unittest.main()
