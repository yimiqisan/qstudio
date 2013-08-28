# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app as app
from frame.platform import urlfetch

from .restful_client import RESTfulAPIClient

__all__ = ['StudioRESTfulAPIClient']


class StudioRESTfulAPIClient(RESTfulAPIClient):

    @property
    def _session(self):
        return urlfetch.session()

    def _http_handler(self, http_method, url, data):
        """增加异步执行的支持

        :data parameters
            - _delay 为 False 时, 同步调用, 有返回结果
                     为 True 时, 异步调用立即执行, 无返回结果
                     为 整数 时, 异步调用延迟 _delay 秒执行, 无返回结果

        """
        if app and app.testing:
            # 测试模式下, 实际不推送任务
            return None
        _delay = data.pop('_delay', False)
        if _delay is not False and _delay is not None:
            from frame.platform.services import taskqueue
            if _delay is True:
                _delay = 0
            countdown = int(_delay) if isinstance(_delay, (int, long, float)) else 0
            return taskqueue.add_url(url_=url, method_=http_method, countdown_=countdown, params=data)
        else:
            return super(StudioRESTfulAPIClient, self)._http_handler(http_method, url, data)
