#! -*- coding: utf-8 -*-
"""
    所有服务的连接缓存模块
    ~~~~~~~~~~~~~~~~~~~~~~~~

    控制所有的服务连接, 包括:

    * backend
    * redis
    * memcache (XXX: 即将废弃)
    * beanstalk
    * gcache (XXX: 未实现)

    Attributes:
        backend: 后端连接池
        redis_master: Redis 主库连接池
        redis_slave: Redis 从库连接池
        memcache: Memcache 连接
        beanstalk: Beanstalk 队列服务
"""


import sys
import types

from flask.helpers import locked_cached_property

from frame.platform import config

class EnginesModule(types.ModuleType):
    """ hack 模块的载入, 确保各个服务连接可以通过属性加载 """

    @locked_cached_property
    def redis(self):
        from flask.ext.redis import Redis
        return Redis()

    @locked_cached_property
    def db(self):
        from frame.platform.sqlalchemy import SQLAlchemy
        return SQLAlchemy()

    @locked_cached_property
    def mail(self):
        from frame.ext.mail import Mail
        return Mail()

    @locked_cached_property
    def _share_redis(self):
        """用于校验access token的redis, 需要从oauth2的redis中读数据

        请勿直接用于应用开发!!

        """
        import os
        import redis
        global_conf = config.load_yaml(os.path.join(os.environ['BASE'], 'config.yaml'))
        app_conf = config.load_yaml(os.path.join(os.environ['BASE'], 'frame/apps/auth/app.yaml'))
        conn_conf = global_conf['APP_AUTH']
        conn_conf.update(app_conf)
        url = conn_conf['REDIS']

        return redis.from_url(url)

old_module = sys.modules[__name__] # 保持引用计数
new_module = sys.modules[__name__] = EnginesModule(__name__, __doc__)
new_module.__dict__.update({
    '__file__': __file__,
    '__path__': __path__,
    '__author__': __author__,
    '__builtins__': __builtins__,
})

