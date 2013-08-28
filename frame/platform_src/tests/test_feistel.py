# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase
from frame.platform.contribs import feistel


class FeistelTestCase(TestCase):

    def test_encrypt(self):
        fei = feistel.Feistel('testcode')
        self.assertEqual(fei.encrypt(1), 543266676324605145L)

    def test_decrypt(self):
        fei = feistel.Feistel('testcode2')
        self.assertEqual(fei.decrypt(65536), 14286978534670983482L)

    def test_encrypt_then_decrypt(self):
        fei = feistel.Feistel('testcode3')
        self.assertEqual(200, fei.decrypt(fei.encrypt(200)))
