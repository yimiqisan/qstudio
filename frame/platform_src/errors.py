# -*- coding:utf-8 -*-

import sys

_self = sys.modules[__name__]


class StudioException(Exception):
    pass


class StudioEnvironError(StudioException):
    pass


class StudioConfigError(StudioException):
    '''
    服务器配置错误，阻止启动
    '''
    pass
