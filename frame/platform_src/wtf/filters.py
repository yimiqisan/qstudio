# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from guokr.platform.contribs import base36
from guokr.platform.apis import community
from iptools import IpRange


def Empty(default):
    """
    Field 定义的 default 是在模板呈现时用于填充表单默认值的,
    因此需要另外定义一个 Empty 过滤器来处理传入空值的情况.

    Args:
        default - 传入空值后替换成的默认值

    """
    def _empty(data):
        return default if not data else data
    return _empty


def Trim():
    """过滤收尾的空格字符"""
    def _trim(data):
        return data.strip() if data else data
    return _trim


def NicknameOrUid2Ukey():
    """将输入的uid或nickname或uid转换成ukey

    警告: 可能会把uid当成nickname (如果真的存在这样的nickname)
          转换, 最好只在panel中使用.

    """

    pattern = re.compile(r'^[a-z0-9]{6}$')

    def _convert(data):
        # 如果就是ukey, 不转换
        if not data or pattern.match(data):
            return data

        # 首先尝试转换nickname
        user = community.user.retrieve(
            retrieve_type='by_nickname',
            nickname=data)
        if user:
            try:
                return user[data]['ukey']
            except KeyError:
                pass

        # 然后尝试转换uid
        if data and data.isdigit():
            value = int(data)
            if value > 0 and value < 2176782336:
                return base36.base36_encode(value).rjust(6, b'0')

        return data

    return _convert


def RegexpSub(pattern, repl, count=0, flags=0):
    """对输入的内容执行正则替换

    参数说明参见 re.sub

    """
    pattern = re.compile(pattern, flags)

    def _convert(data):
        if isinstance(data, basestring):
            data = pattern.sub(repl, data, count)
        return data

    return _convert


def Split(sep=None):
    """切分输入的内容

    参数说明参见 str.split

    """

    def _split(data):
        if isinstance(data, list):
            try:
                data = data[0]
            except IndexError:
                data = ''
        if isinstance(data, basestring):
            data = data.split(sep)
        return data

    return _split


def IP():
    """
        把错误用法转换成正确用法,但首先必须是ipcidr
        正确：
            127.0.0.1
            127.0.0.1/32
            10.0.0.0/32
            10.0.0.0/32
        错误：
            10/16
            10
    """
    def _normalIP(data):
        if not data:
            return data
        try:
            data = data.split('/', 1)
            data[0] = IpRange(data[0])[0]
            data = '/'.join(data)
            return data
        except TypeError:
            return data  # 不规范就不转换了
    return _normalIP
