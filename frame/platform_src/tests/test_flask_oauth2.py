# -*- coding: utf-8 -*-
"""单元测试 frame.platform.flask.oauth2 的模块"""
from __future__ import unicode_literals

import os
import json
from flexmock import flexmock
from werkzeug.urls import url_quote

from frame.platform.flask import Flask
from frame.platform.flask.wrappers import StudioRequest
from frame.platform.flask.testing import TestCase, StudioFlaskClient
from frame.platform.flask.oauth2 import signin_required
from frame.platform.engines import _share_redis


class FlaskOAuth2SigninRequiredTestCase(TestCase):

    def create_app(self):
        Flask.request_class = StudioRequest
        Flask.test_client_class = StudioFlaskClient
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['OAUTH2_CLIENT_ID'] = 100
        app.config['DOMAIN_NAME'] = 'test.guokr.com'
        app.config['SERVER_NAME'] = 'test.guokr.com'
        os.environ['GUOKR_ENVIRON'] = 'STAGING'
        os.environ['GUOKR_SERVER_ACCOUNT'] = 'account.test.guokr.com'

        @signin_required
        def index():
            return 'Yahooooo'

        app.add_url_rule('/', view_func=index, subdomain='www')

        from frame.platform.routing_rules import url_map
        ext_adapter = url_map.bind(
            'test.guokr.com',
            script_name=app.config['APPLICATION_ROOT'] or '/',
            url_scheme=app.config['PREFERRED_URL_SCHEME'])

        def external_url_handler(error, endpoint, values):
            method = values.pop('_method', None)
            anchor = values.pop('_anchor', None)
            values.pop('_external', None)
            rv = ext_adapter.build(endpoint, values, method=method,
                                   force_external=True)
            if anchor is not None:
                rv += '#' + url_quote(anchor)
            return rv

        app.url_build_error_handlers.append(external_url_handler)

        return app

    def setUp(self):
        return

    def tearDown(self):
        return

    def test_decorated_with_cookie(self):
        """测试已装饰且带正确cookie的情况"""
        mock = flexmock(_share_redis)
        (mock
         .should_receive('get')
         .with_args('passport-access-token:ABCD1234')
         .and_return(json.dumps({
             'ukey': 'abcdef',
             'client_id': 100}))
         .once())

        with self.client as c:
            resp = c.get('/', headers={
                'Cookie': '_100_access_token=ABCD1234; _100_ukey=abcdef'},
                subdomain='www')
            self.assert200(resp)
            self.assertEqual(resp.data, 'Yahooooo')

    def test_decorated_with_invalid_cookie(self):
        """测试已装饰但带错误cookie的情况"""
        mock = flexmock(_share_redis)
        (mock.should_receive('get')
         .with_args('passport-access-token:ABCD1234')
         .and_return(json.dumps({
             'ukey': 'abcdef',
             'client_id': 101}))
         .once())

        with self.client as c:
            resp = c.get('/', headers={
                'Cookie': '_100_access_token=ABCD1234; _100_ukey=abcdef'},
                subdomain='www')
            self.assertRedirects(
                resp, 'http://www.test.guokr.com/sso/?suppress_prompt=1&lazy=y&'
                'success=http%3A%2F%2Fwww.test.guokr.com%2F')

    def test_decorated_without_cookie(self):
        mock = flexmock(_share_redis)
        mock.should_receive('get').never()

        with self.client as c:
            resp = c.get('/', subdomain='www')
            self.assertRedirects(
                resp, 'http://www.test.guokr.com/sso/?suppress_prompt=1&lazy=y&'
                'success=http%3A%2F%2Fwww.test.guokr.com%2F')
