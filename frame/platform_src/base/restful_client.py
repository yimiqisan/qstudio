# -*- coding: utf-8 -*-
#from __future__ import unicode_literals
"""
RESTful API 客户端的实现基类

尽量避免对果壳网自己的服务和模块产生依赖, 有依赖的部分应该放在 frame_restful_client.py 下

"""
import sys
import inspect
import urlparse
import requests
from collections import namedtuple

from werkzeug.utils import cached_property

from frame.platform.errors import StudioException
from frame.platform.contribs.encoding import smart_quote

__all__ = ['APIClientError', 'APIServerError', \
           'RESTfulAPIClient', 'APIClientImporter']


class APIClientError(StudioException):

    def __init__(self, errdict):
        self.error = errdict['error']
        self.error_code = errdict['error_code']
        self.request_uri = errdict['request_uri']
        super(APIClientError, self).__init__('%(error_code)s: %(error)s' % errdict)


class APIServerError(StudioException):
    pass


class _RESTfulMixin(object):

    def add_params_handlers(self, *handlers):
        self._client._params_handlers.setdefault(self._name, []).extend(handlers)

    @cached_property
    def _url(self):
        path = self._path + '.json' # use json (perhaps msgpack?)
        return urlparse.urlunparse((self._client._scheme,
            self._client._netloc, path, '', '', ''))

APIPager = namedtuple('APIPager', 'limit total offset')


class RESTfulAPIClient(object):

    HTTP_METHODS = {
        'create': 'POST',
        'retrieve': 'GET',
        'update': 'PUT',
        'delete': 'DELETE',
    }

    global_params_handlers = []

    def __init__(self, netloc, scheme='http'):
        """RESTful 的 API 客户端实现

        :Parameters
            - netloc (string) urlparse 中的 netloc 部分, 可以是函数
            - scheme (string) urlparse 中的 scheme 部分
            - auth_interface (AuthInterface) 验证接口

        """
        self._scheme = scheme
        self.__netloc = netloc
        self._params_handlers = {}
        self._resource_ids = {}
        self._argspec = {}
        self._attributes = {}
        self._S

        if self.global_params_handlers:
            self.add_params_handlers(*self.global_params_handlers)

    def add_params_handlers(self, *handlers):
        self._params_handlers.setdefault('', []).extend(handlers)

    @property
    def _session(self):
        if self._S is None:
            S = requests.Session(timeout=30)
            S.config['keep_alive'] = True
            S.config['base_headers'] = {
                b'User-Agent': b'studio-api-client',
            }
            self._S = S
        return self._S

    def _http_handler(self, http_method, url, data):

        with_pager = data.pop('_with_pager', None)

        # GET 和 DELETE 用 query string
        if http_method in ('GET', 'DELETE'):
            r = self._session.request(method=http_method, url=url, params=data)
        else:
            files = data.pop('_files', None)
            r = self._session.request(method=http_method, url=url, data=data, files=files)

        if r.json:
            if not r.json['ok']:
                raise APIClientError(r.json)
            else:
                result = r.json.get('result') # allows None
        else:
            raise APIServerError('Server doesn\'t response a json. Response: %s' % repr(r.content))
        if with_pager:
            pager = APIPager(r.json.get('limit'), r.json.get('total'), r.json.get('offset'))
            return result, pager
        else:
            return result

    @property
    def _netloc(self):
        if callable(self.__netloc):
            return self.__netloc()
        else:
            return self.__netloc

    def __getattr__(self, attr):
        try:
            return self.__getattribute__(attr)
        except AttributeError:
            ret = _Callable(self, '/' + attr)
            self.__dict__[attr] = ret
            return ret


class _Callable(_RESTfulMixin, object):

    def __init__(self, client, name, path=None):
        self._client = client
        self._name = name
        if path is not None:
            self._path = path
        else:
            self._path = name

    def __getattr__(self, attr):
        try:
            return self.__getattribute__(attr)
        except AttributeError:
            if attr in self._client.HTTP_METHODS:
                ret = _Executable(self._client, attr, self._name, self._path)
            else:
                try:
                    ret = self._client._attributes.get(self._name, {})[attr]
                except KeyError:
                    name = '%s/%s' % (self._name, attr)
                    # 故意不返回 path, 因此 apis.xxx(123).yyy.create 与
                    # apis.xxx.yyy.create 相同
                    ret = _Callable(self._client, name)
            self.__dict__[attr] = ret
            return ret

    def __call__(self, id):
        """操作单条数据"""
        path = '%s/%s' % (self._name, smart_quote(id))
        return _Callable(self._client, self._name, path)

    def __setattr__(self, attr, value):
        super(_Callable, self).__setattr__(attr, value)
        if attr[0] != '_':
            self._client._attributes.setdefault(self._name, {})[attr] = value

    def __str__(self):
        return '_Callable (%s)' % self._name

    def __mock__(self, **kwargs):
        """为避免mock时找不到attr, 先静态创建"""
        from flexmock import flexmock
        for method in self._client.HTTP_METHODS:
            getattr(self, method)
        return flexmock(self, **kwargs)

    __repr__ = __str__


class _Executable(_RESTfulMixin, object):

    def __init__(self, client, method, name, path):
        self._client = client
        self._method = method
        self._path = path
        self._name = name + ':' + method

    def _get_params_handlers(self):
        name, method = self._name.split(':')
        name = self._name.split('/')

        _name = ''
        all_handlers = self._client._params_handlers
        handlers = []
        handlers.extend(all_handlers.get(name.pop(0), []))

        for n in name:
            _name += '/' + n
            handlers.extend(all_handlers.get(_name, []))

        _name += ':' + method
        handlers.extend(all_handlers.get(_name, []))
        return handlers

    def set_argspec(self, func):
        """设置当前调用API接口的参数

        不设置也可以调用, 但设置后可以处理匿名参数, 默认值等

        :Parameter
            - func (function) 定义 argspec 的空函数

        """
        self._client._argspec[self._name] = func

    def _get_callargs(self, args, kwargs):
        func = self._client._argspec.get(self._name)
        if func:
            data = inspect.getcallargs(func, *args, **kwargs)
        elif args:
            raise TypeError('%s() takes exactly 0 arguments (%s given)' % (self._method, len(args)))
        else:
            data = kwargs
        return data

    def __call__(self, *args, **kwargs):

        # TODO: 根据传入参数组装 data
        data = self._get_callargs(args, kwargs)

        method = self._method
        http_method = self._client.HTTP_METHODS[method]

        url = self._url

        # custom params handler
        params_handlers = self._get_params_handlers()
        for handler in params_handlers:
            data = handler(data)

        return self._client._http_handler(http_method, url, data)


class APIClientImporter(object):
    """使用PEP 302实现的Importer hook"""

    def __init__(self, wrapper_module, client, **clients):
        """
        :Parameter
            - prefix
            - client (RESTfulAPIClient) 主客户端对象
            - clients (RESTfulAPIClient) 附属的客户端对象

        """
        self._client = client
        self._wrapper_module = wrapper_module
        self._prefix = wrapper_module + '.'
        self._prefix_cutoff = wrapper_module.count('.') + 1
        self._objects = {}
        self._clients = clients

    def __eq__(self, other):
        return self.__class__.__module__ == other.__class__.__module__ and \
               self.__class__.__name__ == other.__class__.__name__ and \
               self._wrapper_module == other._wrapper_module and \
               self._client == other._client and \
               self._clients == other._clients

    def __ne__(self, other):
        return not self.__eq__(other)

    def install(self):
        sys.meta_path[:] = [x for x in sys.meta_path if self !=x] + [self]

    def find_module(self, fullname, path=None):
        if fullname.startswith(self._prefix):
            return self

    def load_module(self, fullname):
        if fullname in self._objects:
            return self._objects[fullname]
        objname = fullname.split('.', self._prefix_cutoff)[self._prefix_cutoff]
        objname = objname.split('.')
        if objname[0] == 'APIClientError':
            return APIClientError
        elif objname[0] == 'APIServerError':
            return APIServerError
        elif self._clients and objname[0] in self._clients:
            ret = self._clients[objname.pop(0)]
        else:
            ret = self._client
        try:
            for attr in objname:
                ret = getattr(ret, attr)
        except AttributeError:
            raise ImportError('No module named %s' % fullname)
        self._objects[fullname] = ret
        return ret
