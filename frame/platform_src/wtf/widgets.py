# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from random import randint

from flask import url_for
from jinja2 import Markup
from wtforms.widgets import Input, HTMLString


class CaptchaWidget(object):

    def __call__(self, field, **kwargs):
        rand = randint(0, 0xffffffff)
        html = HTMLString(
            '<input type="hidden" name="captcha_rand"'
            ' id="captchaRand" value="%(rand)s">'
            '<img src="%(image)s" id="captchaImage" class="captcha">'
            '<span>看不清<a id="changeCaptchaImage" href="#">换一张</a></span>' % {
                'rand': rand,
                'image': url_for('auth:captcha.main', rand=rand)})
        captcha_field = Input('text')
        return Markup(captcha_field(field, maxlength=4, **kwargs) + html)
