# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase
from frame.platform.contribs import base62


class FeistelTestCase(TestCase):

    def test_encode(self):
        self.assertEqual(base62.base62_encode(15699), b'45d')
        self.assertEqual(base62.base62_encode(0xffffffff),
                         b'4GFfc3')
        self.assertEqual(base62.base62_encode(0xffffffffffffffff),
                         b'lYGhA16ahyf')

    def test_decode(self):
        self.assertEqual(base62.base62_decode('avE4b'), 155305547)
        self.assertEqual(base62.base62_decode('ZZZZZZZZ'), 218340105584895)
