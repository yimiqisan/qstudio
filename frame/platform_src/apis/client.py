# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import urlparse

from flask import request
from flask import current_app as app

from frame.platform import urlfetch
from frame.platform.engines import redis, _share_redis
from frame.platform.base import StudioRESTfulAPIClient, APIClientError, APIServerError

def attach_user_access_token(data):
    if request:
        access_token = request.access_token
        if access_token:
            data = data if data is not None else {}
            data.setdefault('access_token', access_token)
    return data

def attach_client_access_token(data):
    # 测试模式下, 不附加client access token
    if app and app.testing:
        return data
    confident_key = 'confident_access_token:%s' % request.client_id
    access_token = redis.get(confident_key)
    _delay = data.get('_delay', False)
    if _delay is not False and _delay is not None:
        # 异步执行, 不能重试故必须确保 access_token 的合法性
        tmp = _share_redis.get('passport-access-token:%s' % access_token)
        if not tmp: # XXX: 似乎没必要做更强的校验了
            access_token = None
    if not access_token:
        scheme = 'http' # 内部通讯, 不需要走 https
        netloc = os.environ['STUDIO_SERVER_ACCOUNT']
        path = '/oauth2/token/'
        params = {
            'client_id': request.client_id,
            'client_secret': request.client_secret,
            'grant_type': 'client_credentials'
        }
        url = urlparse.urlunparse((scheme, netloc, path, '', '', ''))
        resp = urlfetch.request(method='POST', url=url, data=params)
        result = resp.json
        if not result or 'access_token' not in result:
            raise APIServerError('Exception on retrieving access token: %s' % resp.content)
        access_token = result['access_token']
        expires_in = result['expires_in']
        redis.set(confident_key, access_token)
        expires_in = expires_in if expires_in > 0 else 86400
        redis.expire(confident_key, expires_in)
    if data is not None:
        data['access_token'] = access_token
    else:
        data = {'access_token': access_token}
    return data

class RESTfulOpenAPIClient(StudioRESTfulAPIClient):
    global_params_handlers = [attach_user_access_token]

class RESTfulConfidentOpenAPIClient(StudioRESTfulAPIClient):
    global_params_handlers = [attach_client_access_token]

    def _http_handler(self, http_method, url, data):
        try:
            return super(RESTfulConfidentOpenAPIClient, self)._http_handler(http_method, url, data)
        except APIClientError, ex:
            if ex.error_code == 200004:
                redis.delete('confident_access_token:%s' % request.client_id) # 脏了
                data.pop('access_token')
                data = attach_client_access_token(data)
                # 重试
                return super(RESTfulConfidentOpenAPIClient, self)._http_handler(http_method, url, data)
            raise ex


def get_netloc():
    return os.environ['STUDIO_SERVER_APIS']

client = RESTfulOpenAPIClient(get_netloc)
confidential_client = RESTfulConfidentOpenAPIClient(get_netloc)
