# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import base64
import struct

from flask import request
from flask import current_app as app
from wtforms.validators import Regexp, Length, ValidationError

from guokr.platform.apis import image as imageapi
from guokr.platform.apis import APIClientError
from guokr.platform.contribs.encoding import smart_str, smart_unicode
from guokr.platform.engines import _share_redis
from iptools import IpRange


class Ukey(Regexp):
    """
    校验是否是合法的 ukey.

    """

    def __init__(self, message=None):
        super(Ukey, self).__init__(r'^[0-9a-z]{6}$', message=message)

    def __call__(self, form, field):
        if self.message is None:
            self.message = '非法的ukey'

        super(Ukey, self).__call__(form, field)


class HTTP(Regexp):
    """
    校验是否是合法的HTTP / HTTPS URL.
    """
    def __init__(self, require_tld=True, message=None):
        tld_part = (require_tld and r'\.[a-z]{2,10}' or '')
        regex = (r'^https?://([^/:]+%s|([0-9]{1,3}\.){3}'
                 r'[0-9]{1,3})(:[0-9]+)?(\/.*)?$' % tld_part)
        super(HTTP, self).__init__(regex, re.IGNORECASE, message)

    def __call__(self, form, field):
        if self.message is None:
            self.message = field.gettext('Invalid URL.')

        super(HTTP, self).__call__(form, field)


class Tag(Regexp):
    """
    校验是否是合法的 tag.
    """

    def __init__(self, message=None):
        super(Tag, self).__init__(r'^[0-9a-zA-Z\u00c0-\u02df\u0370-\u03ff'
                                  r'\u0400-\u052f\u3400-\u9fff!~\+ \.\-&,'
                                  r':\uff08\uff09\uff0d\u300a-\u300d·]+$',
                                  message=message)

    def __call__(self, form, field):
        if self.message is None:
            self.message = '非法的tag'

        super(Tag, self).__call__(form, field)


class Nickname(Regexp):
    """
    校验是否是合法的昵称.

    """

    def __init__(self, message=None):
        super(Nickname, self).__init__(
            ur'[\w\u3400-\u4db5\u4e00-\u9fcb.-]{1,20}', message=message)

    def __call__(self, form, field):
        if self.message is None:
            self.message = '昵称仅限中英文、数字、“.”、“-”及“_”'

        super(Nickname, self).__call__(form, field)


class CJKLength(Length):

    @staticmethod
    def cjk_len(text):
        text = smart_unicode(text)
        l = len(text)
        l -= len(re.findall('[\x00-\xff]', text)) / 2.0
        return l

    def __call__(self, form, field):
        l = field.data and self.cjk_len(field.data) or 0
        if l < self.min or self.max != -1 and l > self.max:
            if self.message is None:
                if self.max == -1:
                    self.message = '字段长度不得少于%(min)d个（半角字符算半个）'
                elif self.min == -1:
                    self.message = '字段长度不得多于%(max)d个（半角字符算半个）'
                else:
                    self.message = '字段长度必须在%(min)d到%(max)d之间（半角字符算半个）'

            raise ValueError(self.message % dict(min=self.min, max=self.max))


class ImageHashkey(Regexp):
    """校验是否是合法的图像hashkey

    由于图像的 hashkey 是使用 struct.pack + urlsafe_b64encode 构成的,
    其中含有图像的长、宽和格式等信息. 此 validator 可以校验 hashkey
    是否合法, 并是否包含指定的信息.

    :Parameters
        - min_width (int) 最小宽度, 默认 None 不校验
        - max_width (int) 最大宽度, 默认 None 不校验
        - min_height (int) 最小高度, 默认 None 不校验
        - max_height (int) 最大高度, 默认 None 不校验
        - format_choices (tuple) 允许的文件类型, 可以是GIF, JPEG 和 PNG
        - check_uploader (bool) 通过 API 接口检查图像是否真实存在,
                                且上传者是否是当前用户本人.

    """

    def __init__(self, min_width=0, max_width=-1,
                 min_height=0, max_height=-1,
                 format_choices=None, check_uploader=False,
                 message=None):
        super(ImageHashkey, self).__init__(r'[\w-]{56}', message=message)
        self.min_width = min_width
        self.max_width = max_width
        self.min_height = min_height
        self.max_height = max_height
        self.format_choices = format_choices
        self.check_uploader = check_uploader

    def __call__(self, form, field):
        _set_message = False
        if self.message is None:
            _set_message = True
            self.message = '非法的图像hashkey'

        super(ImageHashkey, self).__call__(form, field)
        if _set_message:
            self.message += ' (%(reason)s)'

        try:
            data = base64.urlsafe_b64decode(smart_str(field.data))
            _, width, height, format_ = struct.unpack(b'<32sII2s', data)
            format_ = {
                'GI': 'GIF',
                'PN': 'PNG',
                'JP': 'JPEG'}[format_]
        except (TypeError, struct.error, KeyError):
            raise ValueError(self.message % {
                'reason': 'hashkey格式错误',
            })

        if width < self.min_width or height < self.min_height or \
           (self.max_width != -1 and width > self.max_width) or \
           (self.max_height != -1 and height > self.max_height):
            raise ValueError(self.message % {
                'reason': '违反长宽限制',
            })

        if self.format_choices and format_ not in self.format_choices:
            raise ValueError(self.message % {
                'reason': '不允许的文件类型',
            })

        if self.check_uploader:
            # 检查是否是当前用户上传的
            try:
                imageapi(field.data).retrieve()
            except APIClientError:
                raise ValueError(self.message % {
                    'reason': '文件不存在或上传用户非法',
                })


class Captcha(object):

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if self.message is None:
            self.message = '验证码错误'
        if app.testing:
            return
        rand = request.form.get('captcha_rand', '')
        challenge = field.data.lower().strip()
        rkey = 'captcha:%s' % rand
        with _share_redis.pipeline() as r:
            r.get(rkey)
            r.delete(rkey)
            captcha, _ = r.execute()
        if captcha != challenge:
            raise ValueError(self.message)


class IPAddr(object):

    """
    校验是否是合法的IP地址，接受IPv4/IPv6/CIDR的格式，不接受端口号
    """

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if self.message is None:
            self.message = "IP地址不规范"
        inputIP = field.data
        try:
            IpRange(inputIP)  # 粗筛，接受10、10/32的输入
        except TypeError:
            raise ValidationError(self.message)


class TimeString(object):

    """
    校验是否是合法的时间格式.
    接受yyyy-mm-dd,比如：2013-7-7
    可选的HH:MM:SS，比如：2013-6-31 11:11:11

    """

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if self.message is None:
            self.message = "时间格式不规范"
        inputString = field.data
        from datetime import datetime
        dtformats = (
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d %H',
            '%Y-%m-%d ',
            '%Y-%m-%d',
            '%Y-%m',
            '%Y')
        dt = None
        for dtf in dtformats:
            try:
                dt = datetime.strptime(inputString, dtf)
                break
            except ValueError:
                continue
        if not dt:
            raise ValidationError(self.message)

ukey = Ukey
nickname = Nickname
cjk_length = CJKLength
image_hashkey = ImageHashkey
http = HTTP
timestring = TimeString
