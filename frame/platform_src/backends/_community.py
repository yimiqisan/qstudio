# -*- coding: utf-8 -*-

from .client import client

# /community/sync_account 参数配置
client.community.sync_account.create.set_argspec(lambda ukey, nickname, unblock=None, _delay=None: None)
client.community.sync_account.update.set_argspec(lambda ukey, nickname=None, avatar_url=None, _delay=None: None)
client.community.sync_account.delete.set_argspec(lambda ukey, _delay=None: None)
