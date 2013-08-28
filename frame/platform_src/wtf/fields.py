# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request
from werkzeug import MultiDict

from wtforms import widgets, ValidationError
from wtforms.fields import Field, StringField, \
    BooleanField as _BooleanField, RadioField as _RadioField

from guokr.platform.contribs import threshold

from .validators import Captcha
from .widgets import CaptchaWidget

_unset_value = object()


class MultipleField(Field):

    widget = widgets.TextInput()

    def __init__(self, unbound_field, label=None, validators=None,
                 min_entries=0, max_entries=None, sep=',', **kwargs):
        super(MultipleField, self).__init__(
            label=label, validators=validators, **kwargs)

        self.unbound_field = unbound_field
        self.short_name = kwargs['_name']
        self._prefix = kwargs['_prefix']
        self.min_entries = min_entries
        self.max_entires = max_entries
        self.sep = sep

    def validate(self, form, extra_validators=tuple()):
        _errors = []
        valuelist = self.data if self.data is not None else []
        self.data = []
        for val in valuelist:
            field = self.unbound_field.bind(form=None,
                                            name=self.short_name,
                                            prefix=self._prefix)
            field.process(MultiDict([(field.name, val)]))
            r = field.validate(form)
            if not r:
                _errors.append(field.errors)
            self.data.append(field.data)

        super(MultipleField, self).validate(form, extra_validators)
        self.errors = _errors + self.errors

        return len(self.errors) == 0

    def process_formdata(self, valuelist):
        self.data = valuelist

    def _value(self):
        if isinstance(self.data, list):
            return self.sep.join(self.data)
        elif not self.data:
            return ''
        else:
            return str(self.data)


class CaptchaField(StringField):
    widget = CaptchaWidget()

    def __init__(self, label='', validators=None, **kwargs):
        validators = validators or [Captcha()]
        super(CaptchaField, self).__init__(label, validators, **kwargs)


class ThresholdField(StringField):

    def __init__(self, label='', maxium=3, timeout=60,
                 key='', distinct_by_user=True,
                 default_form_key=True,
                 default_url_key=False,
                 use_captcha=True, message=None, **kwargs):
        if message is None:
            message = 'Threshold limit exceeded'
        self.maxium = maxium
        self.message = message
        self.use_captcha = use_captcha
        self.timeout = timeout
        self._key = key
        self._form = kwargs.get('_form')
        self.default_form_key = default_form_key
        self.distinct_by_user = distinct_by_user
        self.default_url_key = default_url_key
        self._validators = kwargs.get('validators', [])
        super(ThresholdField, self).__init__(label, **kwargs)

    @property
    def _th(self):
        key = self._key
        if not key:
            if self.default_form_key:
                key += self._form.__class__.__name__
            if self.default_url_key:
                key += request.path  # 用path简洁且避免客户端篡改url
        elif callable(key):  # 允许使用key generator
            key = key()
        if self.distinct_by_user:
            key += request.ukey if request.ukey else 'ANONYM'

        return threshold.Threshold(key, self.maxium, self.timeout)

    @property
    def widget(self):
        if self.use_captcha and not self._th.get():
            return CaptchaWidget()
        else:
            return widgets.HiddenInput()

    def pre_validate(self, form):
        if self.use_captcha and not self._th.get():
            self.validators = self._validators + [Captcha()]

    def post_validate(self, form, validation_stopped):
        if form.errors or self.errors or self._th.set():
            # error happened or not exceeds
            return
        form._errors = None  # reset form._errors
        if not self.use_captcha:
            # without captcha and exceed
            raise ValidationError(self.message)
        else:
            # reset threshold
            self._th.clean()


class BooleanField(_BooleanField):
    """
    wtf 自带的 BooleanField 太坑爹了, 照着 django forms 重新实现了一个
    """

    def process_formdata(self, valuelist):
        if valuelist:
            value = valuelist[0]
        else:
            value = False
        if isinstance(value, basestring) and \
           value.lower() in ('false', 'no', '0'):
            self.data = False
        else:
            self.data = bool(value)

    def _value(self):
        if self.raw_data:
            return unicode(self.raw_data[0])
        else:
            return 'y'


class NullBooleanField(BooleanField):
    """照着 django 抄的 bonus"""

    def process_formdata(self, valuelist):
        if valuelist:
            value = unicode(valuelist[0]).lower()
        else:
            value = None
        if value in ('true', 'yes', '1'):
            self.data = True
        elif value in ('false', 'no', '0'):
            self.data = False
        else:
            self.data = None


class RadioField(_RadioField):
    """
    wtf 自带的 RadioField 不能指定label 的 for 数值
    """
    def choices_just(self, num=3):
        #确保适应 self.choices 的宽度都为 num 数量
        new_choices = []
        for choice in self.choices:
            new_choice = []
            left_num = num - len(choice)
            new_choice = list(choice)
            for i in xrange(max(0, left_num)):
                new_choice.append(None)
            new_choices.append(tuple(new_choice))
        self.choices = new_choices

    def iter_choices(self):
        self.choices_just()
        for value, label, label_id in self.choices:
            yield (value, label, self.coerce(value) == self.data, label_id)

    def __iter__(self):
        opts = dict(widget=self.option_widget, _name=self.name, _form=None)
        for i, (value, label,
                checked, label_id) in enumerate(self.iter_choices()):
            opt = self._Option(label=label, id='%s' % label_id
                               if label_id else (self.id+'-'+str(i)), **opts)
            opt.process(None, value)
            opt.checked = checked
            yield opt

    def pre_validate(self, form):
        for v, _, _ in self.choices:
            if self.data == v:
                break
        else:
            raise ValueError(self.gettext('Not a valid choice'))
