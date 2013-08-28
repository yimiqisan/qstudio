# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""在 flask-sqlalchemy 上的定制扩展"""

import random
import contextlib
import threading

from functools import partial

from flask import g, request
from flask.helpers import locked_cached_property
from sqlalchemy import orm, sql, types, exc
from sqlalchemy.util import OrderedDict, to_list
from sqlalchemy.orm import attributes, loading
from sqlalchemy.ext.compiler import compiles
from flask.ext.sqlalchemy import (SQLAlchemy, _SignallingSession,
                                  _EngineConnector, get_state, BaseQuery)
from flask.ext import sqlalchemy as flask_sqlalchemy


from . import types as custom_types
from . import mutable as custom_mutable
from . import hybrid as custom_hybrid

__all__ = ['SQLAlchemy']


def copy_inst(fromobj, tocls, keys, **extra_kw):
    kwargs = dict((key, getattr(fromobj, key)) for key in keys)
    kwargs.update(extra_kw)
    return tocls(**kwargs)


class PreserveDeleted(object):
    """Preserve deleted decorator

    Tracks "deleted" objects and includes a "restore" feature which will
    "restore" a given row back to the main table.

    Inspired by http://stackoverflow.com/a/13259889, Thanks to zzzeek.

    :Usage

    @db.preserve_deleted(reason=db.Column(db.String(256)))
    class A(db.Model):
        __tablename__ = 'a'

        id = db.Column(db.Integer(), primary_key=True)
        data1 = db.Column(db.String(256))
        data2 = db.Column(db.Text())

    a1, a2 = \
        A(data1='a1d1', data2='a1d2'), \
        A(data1='a2d1', data2='a2d2')

    db.session.add_all([a1, a2])
    db.session.commit()

    assert A.query.order_by(A.id).count() == 2

    db.session.delete(a1, reason='for_fun')
    db.session.commit()

    assert A.query.order_by(A.id).count() == 1

    a1_deleted = A.deleted.query.get(1)
    a1_deleted.restore()
    db.session.commit()

    assert A.deleted.query.count() == 0
    assert A.query.order_by(A.id).count() == 2

    """
    def __init__(self, db, *extra_cols, **kw_extra_cols):
        self.db = db
        self.extra_cols = list(extra_cols)
        if kw_extra_cols:
            for key, col in kw_extra_cols.iteritems():
                if col.key is None:
                    col.key = key
                if col.name is None:
                    col.name = key
                self.extra_cols.append(col)

    def copy_col(self, col):
        newcol = col.copy()
        newcol.constraints = set()
        return newcol

    def __call__(self, class_):

        keys = class_.__table__.c.keys()
        cols = OrderedDict(
            (col.key, self.copy_col(col)) for col in class_.__table__.c)
        for extra_col in self.extra_cols:
            cols[extra_col.key] = extra_col
        cols['__tablename__'] = '%s_deleted' % class_.__table__.name

        db = self.db

        class History(object):
            def restore(self):
                db.session.delete(self)
                instance = copy_inst(self, class_, keys)
                db.session.add(instance)
                instance._deleted = self
                return instance

        hist_class = type(b'%sDeleted' % class_.__name__,
                          (History, db.Model),
                          cols)

        class_.deleted = hist_class

        return class_


class _SignallingSessionMixin(object):

    def get_bind(self, mapper, clause=None):
        # 增加 master/slave 支持
        # mapper is None if someone tries to just get a connection

        if mapper is not None:
            info = getattr(mapper.mapped_table, 'info', {})
            bind_key = info.get('bind_key')
            if bind_key is not None:
                state = get_state(self.app)
                return state.db.get_engine(self.app, bind=bind_key)

        # 通过全局变量 _disable_db_slaves 来控制 slave 行为
        # 不在 request context 内的读操作一律使用主库
        if g and not hasattr(g, 'disable_db_slaves') and \
           isinstance(clause, sql.Select):
            state = get_state(self.app)
            return state.db.get_engine(self.app, bind='__slave__')

        return super(_SignallingSessionMixin, self).get_bind(mapper, clause)

    def delete(self, instance, **extra_kw):
        # 扩展 delete 方法, 在 preserve_deleted 激活时可以传递 extra_cols 的值
        class_ = instance.__class__
        if hasattr(class_, 'deleted'):
            keys = class_.__table__.c.keys()
            h = copy_inst(instance, class_.deleted, keys, **extra_kw)
            self.add(h)

        return super(_SignallingSessionMixin, self).delete(instance)


class _EngineConnectorMixin(object):

    def get_uri(self):
        if self._bind == '__slave__':
            slaves = self._app.config.get(
                'SQLALCHEMY_DATABASE_SLAVE_URIS') or ()
            if slaves:
                return random.choice(slaves)
            else:
                self._bind = None
        if self._bind is None:
            return self._app.config['SQLALCHEMY_DATABASE_URI']
        binds = self._app.config.get('SQLALCHEMY_BINDS') or ()
        assert self._bind in binds, \
            'Bind %r is not specified.  Set it in the SQLALCHEMY_BINDS ' \
            'configuration variable' % self._bind
        return binds[self._bind]


@contextlib.contextmanager
def disable_slaves():
    if g:
        old = getattr(g, 'disable_db_slaves', False)
        g.disable_db_slaves = True
    yield
    if g:
        g.disable_db_slaves = old


def _include_custom(obj):
    for module in custom_types, custom_mutable, custom_hybrid:
        for key in module.__all__:
            if not hasattr(obj, key):
                setattr(obj, key, getattr(module, key))
    obj.disable_slaves = disable_slaves
    obj.current_ukey = current_ukey
    obj.set_current_ukey = set_current_ukey


class SQLAlchemyMixin(object):

    def __init__(self, *args, **kwargs):
        super(SQLAlchemyMixin, self).__init__(*args, **kwargs)
        _include_custom(self)

    def init_app(self, app):
        # 增加 master/slaves 支持
        app.config.setdefault('SQLALCHEMY_DATABASE_SLAVE_URIS', None)
        config_binds = app.config.get('SQLALCHEMY_BINDS')
        if config_binds and '__slave__' in config_binds:
            raise KeyError('__slave__ is a reserved word.')

        return super(SQLAlchemyMixin, self).init_app(app)

    def create_scoped_session(self, options=None):
        """Hepler factory method that creates a scoped session.

        See: https://github.com/mitsuhiko/flask-sqlalchemy/issues/64

        """
        if options is None:
            options = {}
        scopefunc = options.pop('scopefunc', None)
        db = self

        class PartialSignallingSession(_SignallingSession):

            def __init__(self, autocommit=False, autoflush=False):
                (super(PartialSignallingSession, self)
                 .__init__(db, autocommit, autoflush, **options))

        return orm.scoped_session(
            PartialSignallingSession, scopefunc=scopefunc)

    @locked_cached_property
    def preserve_deleted(self):
        return partial(PreserveDeleted, self)

    def make_connector(self, app, bind=None):
        """Creates the connector for a given state and bind."""
        return _EngineConnector(self, app, bind)


class BaseQueryMixin(object):

    def get_or_create(self, **kwargs):
        """Like django's method get_or_create

        Args:
            defaults: Any keyword arguments passed to `filter_by()`
                      except defaults. defaults is a dict, is only use
                      to create an object.

        Returns:
            tuple: (object, is_created)

        """
        mapper = self._only_full_mapper_zero('get_or_create')
        defaults = kwargs.pop('defaults', {})
        instance = self.filter_by(**kwargs).first()
        if instance:
            return instance, False
        else:
            params = {k: v
                      for k, v in kwargs.iteritems()
                      if not isinstance(v, sql.ClauseElement)}
            if defaults:
                params.update(defaults)
            instance = mapper.class_(**params)
            self.session.add(instance)
            return instance, True

    def batch_get(self, *idents):
        mapper = self._only_full_mapper_zero('batch_get')
        lazyload_idents = {}
        or_list = []
        return_list = [None] * len(idents)
        for idx, ident in enumerate(idents):
            if hasattr(ident, '__composite_values__'):
                ident = ident.__coposite_values__()
            ident = to_list(ident)
            if len(ident) != len(mapper.primary_key):
                raise exc.InvalidRequestError(
                    "Incorrect number of values in identifier to formulate "
                    "primary key for query.batch_get(); "
                    "primary key columns are %s" %
                    ','.join("'%s'" % c for c in mapper.primary_key))

            key = mapper.identity_key_from_primary_key(ident)
            if not self._populate_existing and \
                    not mapper.always_refresh and \
                    self._lockmode is None:

                instance = loading.get_from_identity(
                    self.session, key, attributes.PASSIVE_OFF)
                if instance is not None:
                    # reject calls for id in indentity map but class
                    # mismatch.
                    if not issubclass(instance.__class__, mapper.class_):
                        instance = None
                    return_list[idx] = instance
                    continue

            lazyload_idents.setdefault(key[1], []).append(idx)
            and_list = [col == ide for col, ide in
                        zip(mapper.primary_key, ident)]
            or_list.append(sql.and_(*and_list))

        if or_list:
            # 加载未缓存对象到 return_list 中
            for instance in self.filter(sql.or_(*or_list)):
                ident = mapper.primary_key_from_instance(instance)
                for idx in lazyload_idents[tuple(ident)]:
                    return_list[idx] = instance

        return return_list

_SignallingSession = type(_SignallingSession.__name__,
                          (_SignallingSessionMixin, _SignallingSession), {})
_EngineConnector = type(_EngineConnector.__name__,
                        (_EngineConnectorMixin, _EngineConnector), {})
SQLAlchemy = type(SQLAlchemy.__name__,
                  (SQLAlchemyMixin, SQLAlchemy), {})
BaseQuery = type(BaseQuery.__name__,
                 (BaseQueryMixin, BaseQuery), {})

# dirty monkey patch
flask_sqlalchemy.BaseQuery = BaseQuery
flask_sqlalchemy.Model.query_class = BaseQuery


class current_ukey(sql.ColumnElement):
    type = types.String()

imsafe = threading.local()


@compiles(current_ukey)
def default_current_ukey(element, compiler, **kw):
    ukey = getattr(imsafe, '_db_current_ukey', request.ukey
                   if request else None)
    return compiler.process(sql.bindparam('current_ukey', ukey))


@contextlib.contextmanager
def set_current_ukey(ukey):
    imsafe._db_current_ukey = ukey
    yield
    delattr(imsafe, '_db_current_ukey')
