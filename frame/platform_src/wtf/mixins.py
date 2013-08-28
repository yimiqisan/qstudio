# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""各种常用 Mixin 定义"""

from . import shortcut
from flask.ext.wtf import Form, validators, fields

class DraftedForm(Form):
    draft_id = fields.IntegerField('draft_id',
            validators=[
                validators.Optional()])

class OffsetLimitMixin(object):
    offset = shortcut.offset()
    limit = shortcut.limit()
