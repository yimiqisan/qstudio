# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""sqlalchemy.ext.mutable 扩展"""

from sqlalchemy.ext.mutable import Mutable, MutableDict

__all__ = ['MutableList', 'MutableDict']

class MutableList(Mutable, list):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain list to MutableList."""

        if not isinstance(value, MutableList):
            if isinstance(value, (list, tuple)):
                return MutableList(value)

            # this call will raise ValueError
            return super(MutableList, cls).coerce(key, value)
        else:
            return value

    def __delitem__(self, key):
        rv = super(MutableList, self).__delitem__(key)
        self.changed()
        return rv

    def __delslice__(self, key):
        rv = super(MutableList, self).__delslice__(key)
        self.changed()
        return rv

    def __iadd__(self, other):
        rv = super(MutableList, self).__iadd__(other)
        self.changed()
        return rv

    def __imul__(self, other):
        rv = super(MutableList, self).__imul__(other)
        self.changed()
        return rv

    def __setitem__(self, key, value):
        rv = super(MutableList, self).__setitem__(key, value)
        self.changed()
        return rv

    def __setslice__(self, i, j, value):
        rv = super(MutableList, self).__setslice__(i, j, value)
        self.changed()
        return rv

    def append(self, item):
        rv = super(MutableList, self).append(item)
        self.changed()
        return rv

    def remove(self, item):
        rv = super(MutableList, self).remove(item)
        self.changed()
        return rv

    def extend(self, iterable):
        rv = super(MutableList, self).extend(iterable)
        self.changed()
        return rv

    def insert(self, pos, value):
        rv = super(MutableList, self).insert(pos, value)
        self.changed()
        return rv

    def pop(self, index=-1):
        rv = super(MutableList, self).pop(index)
        self.changed()
        return rv

    def reverse(self):
        rv = super(MutableList, self).reverse()
        self.changed()
        return rv

    def sort(self, cmp=None, key=None, reverse=None):
        rv = super(MutableList, self).sort(cmp, key, reverse)
        self.changed()
        return rv
