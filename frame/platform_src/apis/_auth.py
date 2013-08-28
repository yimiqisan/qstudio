# -*- coding: utf-8 -*-

from .client import client
from .client import confidential_client as c_client

# /auth/account 参数配置
client.auth.account.retrieve.set_argspec(lambda: None)
c_client.auth.account.retrieve.set_argspec(lambda ukey=None: None)

# /auth/active_account 参数配置
c_client.auth.active_account.retrieve.set_argspec(
    lambda interval_seconds=864000, order='asc', offset=0, limit=20: None)

# /auth/external_oauth2 参数配置
client.auth.external_oauth2.retrieve.set_argspec(lambda: None)
c_client.auth.external_oauth2.retrieve.set_argspec(lambda ukey=None: None)
