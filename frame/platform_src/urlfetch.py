# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""
    frame.platform.services.urlfetch
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    对 requests 进行了封装, 提供了并行, 统一, 安全的 URL 抓取接口

"""

import os
import requests

S = None

def session():
    global S
    keep_alive = os.environ['STUDIO_UNIFIED_PORT'] == '80'
    if S is None:
        S = requests.Session(
            timeout=30, config={
            'pool_maxsize': 20,
            'keep_alive': keep_alive,
            'base_headers': {
                b'User-Agent': b'Qsrobot',
            }
        })
    return S

request = lambda *args, **kwargs: session().request(*args, **kwargs)
head = lambda url, **kwargs: session().head(url, **kwargs)
get = lambda url, **kwargs: session().get(url, **kwargs)
post = lambda url, data=None, **kwargs: session().post(url, data, **kwargs)
put = lambda url, data=None, **kwargs: session().put(url, data, **kwargs)
patch = lambda url, data=None, **kwargs: session().patch(url, data, **kwargs)
delete = lambda url, **kwargs: session().delete(url, **kwargs)
