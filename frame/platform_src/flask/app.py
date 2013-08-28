# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""
    frame.platform.flask.app
    ~~~~~~~~~~~~~~~~~~~~~~~~

    继承 Flask 实例, 生成 for frame 的 Flask 实例

"""
import os
import sys
# hack sys, 使默认编码为UTF-8
reload(sys)
sys.setdefaultencoding('UTF-8')
from pprint import pformat

from frame.platform.engines import db
from frame.platform.engines import redis
from frame.platform import config
from frame.platform.contribs.monkeypatch import mp_json, tz_datetime

mp_json.patch()
tz_datetime.patch()

import time
from flask import Flask, request, g
from flask.helpers import locked_cached_property
from werkzeug.routing import Map
from werkzeug.urls import url_quote

from jinja2 import FileSystemLoader

from .wrappers import StudioRequest
from .converters import addition_converters
from .testing import StudioFlaskClient
from .session import RedisSessionInterface
from .errors import HTTPException, NotFound, InternalServerError


class StudioFlask(Flask):

    request_class = StudioRequest
    test_client_class = StudioFlaskClient
    session_interface = RedisSessionInterface()

    def __init__(self, *args, **kwargs):
        """
        初始化 Flask 实例

        这里主要绑定了 flask-sqlalchemy 的数据库连接

        """
        super(StudioFlask, self).__init__(*args, **kwargs)

        global_conf = config.load_yaml(os.path.join(
            os.environ['BASE'], 'config.yaml'))
        root_path = os.path.abspath(self.root_path)
        while os.path.exists(
                os.path.join(root_path, '__init__.py')):
            # 强制使用最上层的 app.yaml, 避免子应用使用独立的 app.yaml
            root_path = os.path.dirname(root_path)
        app_conf = config.load_yaml(os.path.join(root_path, 'app.yaml'))
        conn_conf = global_conf['APP_' + app_conf['APPNAME'].upper()]
        conn_conf.setdefault('DOMAIN_NAME', global_conf['DOMAIN_NAME'])
        conn_conf.setdefault('UNIFIED_PORT', global_conf['UNIFIED_PORT'])
        conn_conf.update(app_conf)
        self.config['SQLALCHEMY_ECHO'] = conn_conf['ENABLE_SQL_ECHO']
        self.config['SQLALCHEMY_DATABASE_URI'] = conn_conf['DB_MASTER']
        self.config['SQLALCHEMY_DATABASE_SLAVE_URIS'] = conn_conf['DB_SLAVES']
        self.config['REDIS_URL'] = conn_conf['REDIS']
        self.config['SESSION_COOKIE_DOMAIN_ADAPTIVE'] = True  # cookie域名自适应
        self.config['DEFAULT_SUBDOMAIN'] = 'www'
        conn_conf_whitelist = ['ADMINS',
                               'SECRET_KEY',
                               'DOMAIN_NAME',
                               'ENABLE_APPRAISER',
                               'OAUTH2_CLIENT_ID',
                               'OAUTH2_CLIENT_SECRET',
                               'DEFAULT_AVATAR_HASHKEY',
                               'PANEL_OAUTH2_CLIENT_ID',
                               'PANEL_OAUTH2_CLIENT_SECRET',
                               'PERMANENT_SESSION_LIFETIME',
                               'ENABLE_THRESHOLD_CONTROL']
        for key in conn_conf_whitelist:
            self.config[key] = conn_conf[key]

        self.config.update(app_conf)

        if not self.config['SERVER_NAME']:
            server_name = self.config['DOMAIN_NAME']
            if conn_conf['UNIFIED_PORT'] not in (80, 443):
                server_name += ':' + str(conn_conf['UNIFIED_PORT'])
            self.config['SERVER_NAME'] = server_name
        os.environ['STUDIO_APPNAME'] = appname = self.config['APPNAME']
        db.init_app(self)
        redis.init_app(self)

        if self.config.get('ENABLE_BABEL'):
            from flask.ext.babel import Babel
            self.babel = Babel(self)

        if self.config.get('ENABLE_MAIL'):
            from frame.platform.engines import mail
            mail.init_app(self)

        if not self.debug:
            import logging
            from logging.handlers import SMTPHandler
            # TODO: 有编解码错误
            mail_handler = SMTPHandler(
                '127.0.0.1',
                'server-error@%s' % self.config['DOMAIN_NAME'],
                self.config['ADMINS'],
                'Flask Application "%s" Failed' % appname)
            mail_handler.setLevel(logging.WARNING)
            mail_handler.setFormatter(logging.Formatter(
                "URL:                   %(url)s\n"
                "Message type:          %(levelname)s\n"
                "Location:              %(pathname)s:%(lineno)d\n"
                "Module:                %(module)s\n"
                "Function:              %(funcName)s\n"
                "Time:                  %(asctime)s\n"
                "Method:                %(method)s\n"
                "Ukey:                  %(ukey)s\n"
                "\n"
                "ENVRION:\n"
                "%(environ)s\n"
                "\n"
                "Message:\n"
                "\n"
                "%(message)s\n"))

            self.logger.addHandler(mail_handler)

        # 干掉原来url_map中的static
        self.url_map = Map(default_subdomain=self.config['DEFAULT_SUBDOMAIN'])
        self.url_map.converters.update(addition_converters)

        self.add_url_rule(
            '/<path:filename>', endpoint='static',
            subdomain='static', view_func=self.send_static_file)

        self.add_url_rule(
            '/<path:filename>', endpoint='sslstatic',
            subdomain='sslstatic', view_func=self.send_static_file)

        with self.app_context():
            from . import filters  # noqa pyflakes:ignore
            from . import helpers
            from . import users
            from . import privileges
            from random import choice
            self.jinja_env.globals.update(
                user_home=helpers.user_home,
                resp_image=helpers.resp_image,
                thumbnail_for=helpers.thumbnail_for,
                image_for=helpers.image_for,
                static_file=helpers.static_file,
                preload_user_meta=users.preload_user_meta,
                user_meta=users.user_meta,
                has_privilege=privileges.has_privilege,
                url_signin=helpers.url_signin,
                zip=zip, map=map, enumerate=enumerate,
                pairs=helpers.pairs, random_choice=choice)
            self.jinja_env.add_extension('jinja2.ext.do')
            self.jinja_env.add_extension('jinja2.ext.loopcontrols')

        # 全局 url_for
        self.url_build_error_handlers.append(self._external_url_handler)

        @self.before_request
        def add_x_start():
            g.__x_start = time.time()

        @self.after_request
        def add_x_headers(response):
            try:
                duration = time.time() - g.__x_start
            except AttributeError:
                duration = -0.0001
            response.headers.add(
                b'X-Served-By',
                request.environ.get('uwsgi.node', b'Unknown') or b'Error')
            response.headers.add(b'X-Served-In-Seconds', b'%.4f' % duration)
            return response

        # 开发模式下启用调试器
        self.debugger_wsgi_app = None
        if os.environ['STUDIO_ENVIRON'] == 'DEVELOPMENT' and self.debug:
            # 如果是uwsgi且为单进程模式, 则启用控制台调试器
            try:
                import uwsgi
                evalex = uwsgi.numproc == 1
            except ImportError:
                evalex = True
            from werkzeug.debug import DebuggedApplication
            self.debugger_wsgi_app = DebuggedApplication(self.wsgi_app, evalex)

        # 默认不支持 sso 登录, 可通过方法 enable_sso() 启用
        self.is_sso_enabled = False

        # 绑定默认的 404 和 500 错误处理
        @self.errorhandler(404)
        def page_not_found(error):
            if isinstance(error, HTTPException):
                return error
            else:
                return NotFound('找不到网页')

        @self.errorhandler(500)
        def internal_server_error(error):
            if isinstance(error, HTTPException):
                return error
            else:
                return InternalServerError('服务器内部错误')

    def wsgi_app(self, environ, start_response):
        """插件, 支持指定不带端口号的 DOMAIN_NAME"""
        if 'DOMAIN_NAME' in self.config:
            host = environ.get('HTTP_HOST', '')
            host = host.split(':', 1)
            host[0] = self.config['DOMAIN_NAME']
            self.config['SERVER_NAME'] = ':'.join(host)
        return super(StudioFlask, self).wsgi_app(environ, start_response)

    @property
    def external_url_adapter(self):
        from frame.platform.routing_rules import url_map as external_url_map
        if request:
            external_url_map.bind_to_environ(
                request.environ,
                server_name=self.config['SERVER_NAME'])
        server_name = self.config.get('SERVER_NAME')
        return external_url_map.bind(
            server_name,
            script_name=self.config['APPLICATION_ROOT'] or '/',
            url_scheme=self.config['PREFERRED_URL_SCHEME'])

    def _external_url_handler(self, error, endpoint, values):
        """在本地的 url_for 无法生成链接时, 查找全局路由表"""
        method = values.pop('_method', None)
        anchor = values.pop('_anchor', None)
        values.pop('_external', None)
        ext_adapter = self.external_url_adapter
        if os.environ['STUDIO_ENVIRON'] == 'PRODUCTION':
            # 生产环境中, auth 应用使用 https
            if endpoint[:5] == 'auth:':
                ext_adapter.url_scheme = 'https'
            else:
                ext_adapter.url_scheme = 'http'
        rv = ext_adapter.build(endpoint, values, method=method,
                               force_external=True)
        if anchor is not None:
            rv += '#' + url_quote(anchor)
        return rv

    @locked_cached_property
    def jinja_loader(self):
        """The Jinja loader for this package bound object.

        .. versionadded:: 0.5
        """
        if self.template_folder is not None:
            return FileSystemLoader([
                os.path.join(self.root_path, self.template_folder),
                os.path.join(os.path.abspath(os.path.dirname(__file__)),
                             'templates')])

    def log_exception(self, exc_info):
        """扩展默认的log_exception, 以记录更多的信息"""
        extra = {
            'method': request.method,
            'url': request.url,
            'ukey': getattr(request, 'ukey', None),
            'environ': pformat(request.environ),
        }
        self.logger.error('Exception on %s [%s]' % (
            request.path,
            request.method,
        ), exc_info=exc_info, extra=extra)

    def enable_sso(self, path, subdomain):
        from . import sso
        return sso.enable_sso(self, path, subdomain)

    def __call__(self, environ, start_response):
        if not self.testing and self.debugger_wsgi_app:
            wsgi_app = self.debugger_wsgi_app
        else:
            wsgi_app = self.wsgi_app
        return wsgi_app(environ, start_response)
