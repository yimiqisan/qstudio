# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import wraps
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper

__all__ = []


def hybrid_column(relation, class_=None, expression=None,
                  class_kwargs=None, default=''):

    if isinstance(class_, type):
        class_ = mapper.class_mapper(class_, compile=False)

    if class_kwargs is None:
        class_kwargs = {}
    def decorate(func):

        name = func.__name__

        @wraps(func)
        def fget(self):
            obj = getattr(self, relation)
            if not obj:
                return default
            else:
                return getattr(obj.name)

        hybrid = hybrid_property(fget)

        if class_:
            def fset(self, value):
                obj = getattr(self, relation)
                if not obj:
                    obj = class_(**class_kwargs)
                    setattr(self, relation, obj)
                setattr(obj, name, value)
            hybrid.setter(fset)

        if expression:
            def expr(cls):
                return expression
            hybrid.expression(expr)

        return hybrid

