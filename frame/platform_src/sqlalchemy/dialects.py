# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""自定义sqlalchemy的各种方言"""

from sqlalchemy.sql import expression, operators
from sqlalchemy.ext.compiler import compiles

@compiles(expression._UnaryExpression, 'sqlite')
def sqlite_unary(element, compiler, **kw):
    if element.modifier == operators.nullslast_op:
        inner = element.element
        ret = "CASE WHEN %s IS NULL THEN 1 ELSE 0 END, %s" % (
            compiler.process(inner.element), compiler.visit_unary(inner))
    elif element.modifier == operators.nullsfirst_op:
        inner = element.element
        ret = "CASE WHEN %s IS NULL THEN 0 ELSE 1 END, %s" % (
            compiler.process(inner.element), compiler.visit_unary(inner))
    else:
        ret = compiler.visit_unary(element, **kw)
    return ret
