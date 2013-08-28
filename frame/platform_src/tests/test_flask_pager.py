# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""flask.pager 单元测试"""

from flask import Flask
from jinja2 import Markup
from flask.ext.testing import TestCase
from frame.platform.flask.pager import Pager

class FlaskPagerTestCase(TestCase):

    def create_app(self):
        app = Flask('frame.platform.flask')
        return app

    def test_current_page(self):
        with self.app.test_request_context('/test?page=5'):
            p = Pager(10, 130)
            self.assertEqual(p.current_page, 5)

        with self.app.test_request_context('/test?page=15'):
            p = Pager(10, 130)
            self.assertEqual(p.current_page, 13)

        with self.app.test_request_context('/test?page=0'):
            p = Pager(10, 130)
            self.assertEqual(p.current_page, 1)

        with self.app.test_request_context('/test'):
            p = Pager(10, 0)
            self.assertEqual(p.current_page, 1)

    def test_prev_page(self):
        with self.app.test_request_context('/test'):
            p = Pager(10, 130)
            self.assertEqual(p.prev_page, None)

        with self.app.test_request_context('/test?page=2'):
            p = Pager(10, 130)
            self.assertEqual(p.prev_page, 1)

    def test_next_page(self):
        with self.app.test_request_context('/test?page=13'):
            p = Pager(10, 130)
            self.assertEqual(p.next_page, None)

        with self.app.test_request_context('/test?page=12'):
            p = Pager(10, 130)
            self.assertEqual(p.next_page, 13)

    def test_current_offset(self):
        with self.app.test_request_context('/test?page=3'):
            p = Pager(10, 130)
            self.assertEqual(p.current_offset, 20)

        with self.app.test_request_context('/test?page=15'):
            p = Pager(10, 130)
            self.assertEqual(p.current_offset, 120)

    def test_total_pages(self):
        with self.app.test_request_context('/test'):
            p = Pager(10, 130)
            self.assertEqual(p.total_pages, 13)

        with self.app.test_request_context('/test'):
            p = Pager(10, 124)
            self.assertEqual(p.total_pages, 13)

        with self.app.test_request_context('/test'):
            p = Pager(10, 134)
            self.assertEqual(p.total_pages, 14)

        with self.app.test_request_context('/test'):
            p = Pager(1, 44)
            self.assertEqual(p.total_pages, 44)

    def test_url_for(self):
        with self.app.test_request_context('/test?b=2&a=1&c=c2&c=c1&page=5'):
            p = Pager(10, 130)
            self.assertEqual(p.url_for(7), '/test?a=1&b=2&c=c2&c=c1&page=7')

    def test_range_pages(self):
        with self.app.test_request_context('/test?page=7'):
            p = Pager(10, 270)
            # 左溢出, 左6右8 (向右补全)
            self.assertEqual(p.range_pages(15), range(1, 16))
            # 左溢出, 左6右20 (全部显示, 向右补全后导致右溢出)
            self.assertEqual(p.range_pages(30), range(1, 28))
            # 左右均溢出, 全部显示
            self.assertEqual(p.range_pages(300), range(1, 28))
            # 无溢出, 奇数个, 左4右4
            self.assertEqual(p.range_pages(9), range(3, 12))
            # 无溢出, 偶数个, 左4右3
            self.assertEqual(p.range_pages(8), range(3, 11))
            p = Pager(10, 100)
            # 右溢出, 左5右3 (向左补全)
            self.assertEqual(p.range_pages(9), range(2, 11))
            # 右溢出, 左6右3 (全部显示, 向左补全后导致左溢出)
            self.assertEqual(p.range_pages(12), range(1, 11))

    def test_call(self):
        with self.app.test_request_context('/test?a=1&page=5'):
            p = Pager(10, 130)
            s = p(10)
            self.assertTrue(isinstance(s, Markup))
            self.assertTrue(len(s) > 0)
