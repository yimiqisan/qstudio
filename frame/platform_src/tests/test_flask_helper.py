# -*- coding: utf-8 -*-
"""单元测试 frame.platform.flask.helpers 的模块"""
from __future__ import unicode_literals

import os

from frame.platform.flask import Flask
from frame.platform.flask.wrappers import StudioRequest
from frame.platform.flask.testing import TestCase, StudioFlaskClient
from frame.platform.flask.helpers import url2hashkey


class Url2hashkeyTestCase(TestCase):

    def setUp(self):
        return

    def create_app(self):
        Flask.request_class = StudioRequest
        Flask.test_client_class = StudioFlaskClient
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['OAUTH2_CLIENT_ID'] = 100
        app.config['DOMAIN_NAME'] = 'test.guokr.com'
        app.config['SERVER_NAME'] = 'test.guokr.com'
        os.environ['STUDIO_ENVIRON'] = 'STAGING'
        os.environ['STUDIO_SERVER_ACCOUNT'] = 'account.test.guokr.com'
        return app

    def test_url2hashkey(self):
        thumbnail_url = (
            'http://img1.guokr.com/thumbnail/'
            'BYq-qCvN39IP5Px-UyKzC39vDHp2CMqYQuB4Wu1X'
            'C6uQBwAAIAoAAEpQ_480x642.jpg')

        image_url = (
            'http://img1.guokr.com/image/87KHPNucv'
            'o3YuEJWmldH8WnnBjr3YXaJ823Rq6t9JXA0AgAAYAEAAEpQ.jpg')

        self.assertTrue('87KHPNu' in url2hashkey(image_url))
        self.assertTrue(url2hashkey(thumbnail_url) is None)
        self.assertTrue('87KHPNu' in url2hashkey(
            image_url, take_thumbnail=True))
        self.assertTrue('BYq-qCv' in url2hashkey(
            thumbnail_url, take_thumbnail=True))
