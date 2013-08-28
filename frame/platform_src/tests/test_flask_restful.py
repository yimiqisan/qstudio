# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import unittest

from flexmock import flexmock
from frame.platform.flask import RESTfulAPI

class RESTfulAPITestCase(unittest.TestCase):

    def setUp(self):
        pass

    def test_attach_to(self):
        app = flexmock()
        fake_view = 'DOkde'
        flexmock(RESTfulAPI).should_receive('as_view').and_return(fake_view)
        RESTfulAPI.resource_path = '/test'
        app.should_receive('add_url_rule').with_args(
            rule='/test.<fileext:_format>',
            endpoint='restfulapi',
            view_func=fake_view,
            defaults={'_urlmethod': None},
            subdomain=None,
            methods=['GET', 'POST', 'PUT', 'DELETE']
        ).twice()
        app.should_receive('add_url_rule').with_args(
            rule='/test/<urlmethod:_urlmethod>.<fileext:_format>',
            endpoint='restfulapi_method',
            view_func=fake_view,
            subdomain=None,
            methods=['POST']
        ).twice()
        RESTfulAPI.attach_to(app)
        RESTfulAPI.resource_id = 'testid'
        app.should_receive('add_url_rule').with_args(
            rule='/test/<int:testid>.<fileext:_format>',
            endpoint='restfulapi',
            view_func=fake_view,
            defaults={'_urlmethod': None},
            subdomain=None,
            methods=['GET', 'POST', 'PUT', 'DELETE']
        ).once()
        app.should_receive('add_url_rule').with_args(
            rule='/test/<int:testid>/<urlmethod:_urlmethod>.<fileext:_format>',
            endpoint='restfulapi_method',
            view_func=fake_view,
            subdomain=None,
            methods=['POST']
        ).once()
        RESTfulAPI.attach_to(app)

if __name__ == '__main__':
    unittest.main()
