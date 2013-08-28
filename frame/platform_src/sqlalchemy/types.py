# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""custom types"""

import socket
import struct
import anyjson as json
import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import TypeDecorator, LargeBinary, CHAR, \
    Integer, String, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID, INET, CIDR
from iptools import IpRange
import uuid

__all__ = ['JSONType', 'HashkeyType', 'LowerString', 'GUID', 'IPv4Address']


class LowerString(TypeDecorator):

    impl = String

    def process_bind_param(self, value, dialect):
        return value.lower()


class JSONType(TypeDecorator):

    impl = LargeBinary

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class HashkeyType(TypeDecorator):

    impl = CHAR

    def __init__(self, empty=None):
        self.__empty = empty
        super(HashkeyType, self).__init__(56)

    def process_result_value(self, value, dialect):
        """处理 hashkey == None 时的默认值转换

        自动转换成 self.__empty.

        所以说, null 是一个很独特的状态, 一个没有了就不能重来的状态.

        """
        if value is None:
            value = self.__empty
        return value


class GUID(TypeDecorator):

    """Platform-independent GUID type.

    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    """
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value)
            else:
                # hexstring
                return "%.32x" % value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return uuid.UUID(value)


def cidr2bigint(value):
    return struct.unpack(b'>Q',
                         socket.inet_aton(IpRange(value)[0]) +
                         socket.inet_aton(IpRange(value)[-1])
                         )[0]


def bigint2cidr(value):
    start, stop = value >> 32, value & 0xffffffff
    iprange = 34 - len(bin(stop - start))
    ipstart = socket.inet_ntoa(struct.pack(b'>I', start))
    return '%s/%s' % (ipstart, iprange)


class cidr_contains(sa.sql.expression.FunctionElement):
    type = Boolean()
    name = 'cidr_contains'


@compiles(cidr_contains)
def default_cidr_contains(element, compiler, **kw):
    params = element.clauses
    if len(params) != 2:
        raise ValueError()

    results = []
    for param in params:
        if hasattr(param, 'value'):
            value = cidr2bigint(param.value)
            upper = sa.literal(value >> 32)
            lower = sa.literal(value & 0xffffffff)
        elif isinstance(param.type, IPCIDR):
            upper = param.op('>>')(sa.literal(32))
            lower = param.op('&')(sa.literal(0xffffffff))
        else:  # param.type == IPv4Address
            upper = param
            lower = param
        results.append((upper, lower))
    return compiler.process(
        sa.and_(results[0][0] <= results[1][0],
                results[0][1] >= results[1][1]))


@compiles(cidr_contains, 'postgresql')
def postgres_cidr_contains(element, compiler, **kw):
    expr, other = element.clauses
    return compiler.process(expr.op('>>=')(other))


class IPv4Address(TypeDecorator):

    """Platform-independent IPv4 address type."""

    impl = Integer

    class Comparator(Integer.Comparator):

        """Define comparison operations for :class:`.OPCIDR`."""

        def contains(self, other, **kwargs):
            """Boolean expression.  Test if elements are a superset of the
            elements of the argument array expression.
            """
            # return self in IpRange(other)
            return cidr_contains(self.expr, other)

        def contained_by(self, other):
            """Boolean expression.  Test if elements are a proper subset of the
            elements of the argument array expression.
            """
            return cidr_contains(other, self.expr)

    @property
    def comparator_factory(self):
        return self.Comparator

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(INET())
        else:
            return dialect.type_descriptor(Integer())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            # big-endian
            return struct.unpack(b'>I', socket.inet_aton(value))[0]

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            # big-endian
            return socket.inet_ntoa(struct.pack(b'>I', value))


class IPCIDR(TypeDecorator):

    """Platform-independent IP CIDR address type"""
    impl = BigInteger

    class Comparator(BigInteger.Comparator):

        """Define comparison operations for :class:`.OPCIDR`."""

        def contains(self, other, **kwargs):
            """Boolean expression.  Test if elements are a superset of the
            elements of the argument array expression.
            """
            # return self in IpRange(other)
            return cidr_contains(self.expr, other)

        def contained_by(self, other):
            """Boolean expression.  Test if elements are a proper subset of the
            elements of the argument array expression.
            """
            return cidr_contains(other, self.expr)

    @property
    def comparator_factory(self):
        return self.Comparator

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(CIDR())
        else:
            return dialect.type_descriptor(BigInteger())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            # big-endian,unsigned long long
            return cidr2bigint(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            # big-endian，前32位和后32位分割开
            return bigint2cidr(value)
