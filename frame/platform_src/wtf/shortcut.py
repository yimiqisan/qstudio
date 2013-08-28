# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from . import (filters,
               fields as my_fields,
               validators as my_validators)
from flask.ext.wtf import fields, validators


def _filters(kwargs):
    f = []
    try:
        f.append(filters.Empty(kwargs['empty']))
    except KeyError:
        pass
    if kwargs.get('trim'):
        f.append(filters.Trim())
    return f


def _validators(kwargs):
    v = []
    if kwargs.get('input_required'):
        v.append(validators.InputRequired())
    elif kwargs.get('required'):
        v.append(validators.Required())
    else:
        v.append(validators.Optional())
    min, max = kwargs.get('min'), kwargs.get('max')
    if min or max:
        v.append(validators.NumberRange(min, max))
    min_length, max_length = (kwargs.get('min_length', -1),
                              kwargs.get('max_length', -1))
    if min_length is None:
        min_length = -1
    if max_length is None:
        max_length = -1
    if min_length != -1 or max_length != -1:
        v.append(validators.Length(min_length, max_length))
    cjk_min_length, cjk_max_length = (kwargs.get('cjk_min_length', -1),
                                      kwargs.get('cjk_max_length', -1))
    if cjk_min_length is None:
        cjk_min_length = -1
    if cjk_max_length is None:
        cjk_max_length = -1
    if cjk_min_length != -1 or cjk_max_length != -1:
        v.append(my_validators.CJKLength(cjk_min_length, cjk_max_length))
    choices = kwargs.get('choices')
    if choices:
        v.append(validators.AnyOf(choices))
    if kwargs.get('ukey'):
        v.append(my_validators.Ukey())
    if kwargs.get('nickname'):
        v.append(my_validators.Nickname())
    if kwargs.get('email'):
        v.append(validators.Email())
    if kwargs.get('url'):
        require_tld = kwargs.get('require_tld')
        v.append(validators.URL(require_tld=require_tld))
    if kwargs.get('http'):
        require_tld = kwargs.get('require_tld')
        v.append(my_validators.HTTP(require_tld=require_tld))
    regexp = kwargs.get('regexp')
    if regexp:
        v.append(validators.Regexp(regexp))
    return v


def plain(required=False, **kwargs):
    """校验但不进行任何值转换"""
    kwargs.update({'required': required})
    return fields.Field(
        filters=_filters(kwargs),
        validators=_validators(kwargs))


def integer(min=None, max=None, required=False, **kwargs):
    """校验且转换值为整数"""
    kwargs.update({
        'min': min,
        'max': max,
        'input_required': required})
    return fields.IntegerField(
        filters=_filters(kwargs),
        validators=_validators(kwargs))


def ident(required=False):
    """校验且确保值为合法的id"""
    return integer(min=1, required=required)


def string(min_length=None, max_length=None, required=False, **kwargs):
    """校验且转换值为字符串"""
    kwargs.update({
        'min_length': min_length,
        'max_length': max_length,
        'required': required})
    return fields.StringField(
        filters=_filters(kwargs),
        validators=_validators(kwargs))


def boolean(required=False, **kwargs):
    """校验且转换值为布尔值"""
    kwargs.update({'required': required})
    return my_fields.BooleanField(  # wtf 原生的 BooleanField 太坑爹
        filters=_filters(kwargs),
        validators=_validators(kwargs))


def nullboolean(required=False, **kwargs):
    """校验且转换为布尔值或None"""
    kwargs.update({'required': required})
    return my_fields.NullBooleanField(
        filters=_filters(kwargs),
        validators=_validators(kwargs))


def captcha():
    """校验码校验"""
    kwargs = {'required': True}
    return my_fields.CaptchaField(
        validators=_validators(kwargs))


def multiple(subfield, min_entries=0,
             max_entries=None, required=False, **kwargs):
    """多值支持"""
    kwargs.update({'required': required})
    return my_fields.MultipleField(
        subfield,
        min_entries=min_entries,
        max_entries=max_entries,
        filters=_filters(kwargs),
        validators=_validators(kwargs))


def offset():
    """偏移量校验"""
    return integer(min=0, empty=0, required=False)


def limit():
    """长度限制校验"""
    return integer(min=0, max=5000, empty=20, required=False)


def ukey(required=False):
    """ukey校验"""
    return string(ukey=True, required=required)


def email(required=False):
    """email校验"""
    return string(email=True, required=required)


def url(require_tld=True, required=False):
    return string(url=True, require_tld=require_tld, required=required)


def http(require_tld=True, required=False):
    return string(http=True, require_tld=require_tld, required=required)


def nickname(required=False):
    """nickname校验"""
    return string(nickname=True, cjk_max_length=10, required=required)


def regexp(regexp, required=False):
    return string(regexp=regexp, required=required)


def tag(required=False):
    r = (r'^[0-9a-zA-Z\u00c0-\u02df\u0370-\u03ff'
         r'\u0400-\u052f\u3400-\u9fff!~\+ \.\-&,'
         r':\uff08\uff09\uff0d\u300a-\u300d·]+$')
    return string(regexp=r, required=required)


def hashkey(min_width=0, max_width=-1,
            min_height=0, max_height=-1,
            format_choices=None, check_uploader=False,
            required=False, **kwargs):
    kwargs.update({'required': required})
    v = _validators(kwargs)
    v.append(my_validators.ImageHashkey(min_width, max_width, min_height,
                                        max_height, format_choices,
                                        check_uploader))
    return fields.HiddenField(filters=_filters(kwargs), validators=v)
