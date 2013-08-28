# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase
from frame.platform.wtf.fields import MultipleField

from wtforms import Form
from wtforms import fields
from wtforms import validators
from werkzeug.datastructures import MultiDict

class FieldsTestCase(TestCase):

    def test_multiple_field(self):

        class TestForm(Form):
            m=MultipleField(fields.StringField(validators=[
                validators.Required(), validators.Email()]))

        form_data = MultiDict([('m', '1'), ('m', '2')])
        form = TestForm(form_data)
        self.assertFalse(form.validate())
        self.assertEqual(form.errors['m'][0][0], 'Invalid email address.')

        form_data = MultiDict([('m', 'abc@guokr.com'), ('m', 'wtf@guokr.com')])
        form = TestForm(form_data)
        self.assertTrue(form.validate())
        self.assertEqual(form.m.data, ['abc@guokr.com', 'wtf@guokr.com'])

        form_data = MultiDict([])
        form = TestForm(form_data)
        self.assertTrue(form.validate())
        self.assertEqual(form.m.data, [])

        class Test2Form(Form):
            m=MultipleField(fields.StringField(validators=[
                validators.Required(), validators.Email()]),
                validators=[validators.Required()])

        form_data = MultiDict([])
        form = Test2Form(form_data)
        self.assertFalse(form.validate())
        self.assertEqual(form.errors['m'][0], 'This field is required.')
