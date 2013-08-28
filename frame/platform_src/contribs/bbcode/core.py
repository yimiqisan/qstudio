# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""A minimal but pluggable BBCode parser"""

import weakref
import anyjson as json
from collections import OrderedDict
from werkzeug import utils
from cssselect.parser import Element, CombinedSelector
import cssselect

from ..encoding import smart_unicode

__all__ = ['BBCode']

_NODES = OrderedDict()
_REGEX_NODES = OrderedDict()
_HOOKS = {}
MAXIMUM_DEPTH = 256

class BBCodeSyntaxError(Exception):
    pass

class NodeError(Exception):
    pass

class BaseNode(object):
    """表示一个节点的 object"""

    name = None
    tag_includes = None
    tag_excludes = None
    display = 'inline'

    def __init__(self, value, children=None):
        self.value = value
        if children is None:
            children = []
        self.children = children
        for child in children:
            child.__bind_parent(self)
        self.__parent = None

    def __bind_parent(self, parent):
        self.__parent = weakref.proxy(parent)

    def _filter(self, selector):
        result = []
        # 目前只支持"url"和"li url"这两种写法
        if isinstance(selector, Element):
            if selector.element == self.name:
                result.append(self)
                return result
            children = self.children
            subselector = selector
        elif isinstance(selector, CombinedSelector) and selector.combinator == ' ':
            children = self._filter(selector.selector)
            subselector = selector.subselector
        else:
            raise ValueError('Unsupported selector: %s' % repr(selector))

        if subselector:
            for child in children:
                result.extend(child._filter(subselector))

        return result

    def offset_sibling(self, offset):
        parent = self.__parent
        if not parent:
            return
        try:
            idx = parent.children.index(self) + offset
        except IndexError:
            return
        if idx > -1 and idx < len(parent.children):
            return parent.children[idx]
        else:
            return None

    def prev_sibling(self):
        return self.offset_sibling(-1)

    def next_sibling(self):
        return self.offset_sibling(1)

    @classmethod
    def NODES(cls, BASE_NODES):
        """给出可以内嵌的节点类型

        :Parameters
            - BASE_NODES (OrderedDict) 上层节点允许内嵌的所有节点类型

        :Returns
            NODES OrderedDict

        """
        n = BASE_NODES.copy()
        if cls.tag_includes is not None:
            n = OrderedDict([(tagname, val) for tagname, val in n.iteritems() \
                      if tagname in cls.tag_includes])
        if cls.tag_excludes is not None:
            for tagname in cls.tag_excludes:
                n.pop(tagname, None)
        return n

    def children_html(self, **kwargs):
        """给出所有子节点的HTML文本"""
        return ''.join(map(lambda n: n.html(**kwargs), self.children))

    def children_unicode(self):
        """给出所有子节点的BBCode文本"""
        return ''.join(map(unicode, self.children))

    def children_text(self):
        """给出所有子节点去掉HTML标记后的纯文本"""
        return ''.join(map(lambda n: n.text(), self.children))

    def text(self):
        if self.name is None:
            raise NotImplementedError
        return self.children_text()

    def html(self, **kwargs):
        raise NotImplementedError

    def __html__(self):
        return self.html()

    def __unicode__(self):
        if self.name is None:
            raise NotImplementedError
        ret = '[' + self.name
        if self.value:
            escaped = json.dumps(self.value) # 用 json 来转义
            ret += '=' + escaped
        ret += ']'
        if self.children:
            ret += self.children_unicode()
        ret += '[/' + self.name + ']'
        return ret

    def __str__(self):
        return unicode(self).encode('U8')

    def __repr__(self):
        if self.name is None:
            raise NotImplementedError
        return '%s(%s, %s)' % (
            self.__class__.__name__,
            repr(self.value),
            repr(self.children))

    def __nonzero__(self):
        return bool(self.value or self.children)

class PlainNode(BaseNode):

    name = '__plain__'

    @property
    def has_linebreak(self):
        return '\n' in self.value

    def text(self):
        return self.value

    def html(self, br=True, **kwargs):
        ret = utils.escape(self.value)
        prev_sibling = self.prev_sibling()
        if br and ret[-1:] == '\n' and (
           prev_sibling is None or prev_sibling.display == 'inline'):
            ret = ret[:-1] + '<br />\n'
        return ret

    def __unicode__(self):
        return self.value

class RegexNode(BaseNode):

    name = '__regex__'
    regex = None

    def text(self):
        return self.value.group(0)

    def __unicode__(self):
        return self.value.group(0)

class TopNode(BaseNode):

    name = '__top__'

    def html(self, **kwargs):
        return self.children_html(**kwargs)

    def __unicode__(self):
        return self.children_unicode()

def next_not_escaped_markup(source, markup):
    length = len(source)
    end = 0
    while end < length:
        end = source.find(markup, end)
        if not end or source[end - 1] != '\\':
            return source[:end], end
        end += 1
    else:
        # not found
        raise BBCodeSyntaxError()

def register_node(tagname, *aliases, **kwargs):
    weight = kwargs.pop('weight', len(tagname))
    sorted_key = lambda k: k[1][0]
    def decorator(cls):
        global _NODES, _REGEX_NODES
        if issubclass(cls, RegexNode):
            _REGEX_NODES[tagname] = (weight, cls)
            _REGEX_NODES = OrderedDict(sorted(_REGEX_NODES.items(), key=sorted_key, reverse=True))
            return cls
        if tagname[0] != '_':
            # 带下划线的是内部节点, 不注册
            _NODES[tagname] = (weight, cls)
        for alias in aliases:
            _AliasNode = type(
                cls.__name__ + b'Alias' + str(alias.capitalize()),
                (cls, ), {
                    'name': alias,
                })
            _NODES[alias] = (len(alias), _AliasNode)
        _NODES = OrderedDict(sorted(_NODES.items(), key=sorted_key, reverse=True))
        return cls
    return decorator

def register_hook(hookname):
    def decorator(func):
        _HOOKS.setdefault(hookname, []).append(func)
        return func
    return decorator

def trigger_hook(hookname, *args, **kwargs):
    for func in _HOOKS.get(hookname, []):
        func(*args, **kwargs)

class BBCode(object):

    def __init__(self, source):
        # convert to unix
        source = smart_unicode(source)
        self.source = (source.replace('\r\n', '\n')
                             .replace('\r', '\n')
                             .replace('\u00a0', ' ')) # 不换行空格
        self.stack = []

    def __call__(self, selector):
        return self.filter(selector)

    def filter(self, selector):
        selectors = cssselect.parse(selector)
        result = []
        for sele in selectors:
            result.extend(self.nodes._filter(sele.parsed_tree))
        return result

    @staticmethod
    def len_lstrip(text):
        length = len(text)
        text = text.lstrip()
        return length - len(text), text

    def parse_left(self, source, NODES, REGEX_NODES):
        offset = 1
        add, part = self.len_lstrip(source[1:])
        offset += add
        # 这里从最长的 tagname 开始匹配, 避免互相干扰
        for tagname, (t_length, node_class) in NODES.iteritems():
            if part[:t_length].lower() == tagname:
                break
        else:
            # markup Not found
            raise BBCodeSyntaxError(offset)
    
        add, part = self.len_lstrip(part[t_length:])
        offset += t_length + add
        if part[:1] == ']':
            value = None
        elif part[:1] == '=':
            add, part = self.len_lstrip(part[1:])
            offset += 1 + add
            if part[:1] == '"': # 允许双引号
                part = part[1:]
                offset += 1
                try:
                    value, end = next_not_escaped_markup(part, '"')
                except BBCodeSyntaxError:
                    raise BBCodeSyntaxError(offset)
                add, part = self.len_lstrip(part[end + 1:])
                offset += 1 + end + add
                if part[:1] != ']':
                    raise BBCodeSyntaxError(offset)
                try:
                    value = json.loads('"' + value + '"')
                except ValueError:
                    raise BBCodeSyntaxError(offset)
            elif part[:1] == "'": # 允许单引号
                part = part[1:]
                offset += 1
                try:
                    value, end = next_not_escaped_markup(part, "'")
                except BBCodeSyntaxError:
                    raise BBCodeSyntaxError(offset)
                add, part = self.len_lstrip(part[end + 1:])
                offset += 1 + end + add
                if part[:1] != ']':
                    raise BBCodeSyntaxError(offset)
                try:
                    value = json.loads('"' + value + '"')
                except ValueError:
                    raise BBCodeSyntaxError(offset)
            else:
                try:
                    value, end = next_not_escaped_markup(part, ']')
                except BBCodeSyntaxError:
                    raise BBCodeSyntaxError(offset)
                add, part = self.len_lstrip(part[end:])
                offset += end + add
                try:
                    value = json.loads('"' + value.replace('"', '\\"').replace('\n', '\\n').replace("'", "\\'").replace('\\', '\\\\') + '"')
                except ValueError:
                    raise BBCodeSyntaxError(offset)
        else:
            # not a tag
            raise BBCodeSyntaxError(offset)
    
        part = part[1:]
        offset += 1
        if len(self.stack) < MAXIMUM_DEPTH:
            self.stack.append((tagname, t_length))
        else:
            raise BBCodeSyntaxError(offset)
        add, nodelist = self.parse(part, node_class.NODES(NODES), node_class.NODES(REGEX_NODES))
        offset += add
        try:
            return offset, node_class(value, nodelist)
        except NodeError:
            raise BBCodeSyntaxError(offset)
    
    def parse_right(self, source):
        offset = 1
        if not self.stack:
            raise BBCodeSyntaxError(offset)
        add, part = self.len_lstrip(source[1:])
        offset += add
        if part[:1] != '/':
            raise BBCodeSyntaxError(offset)
        add, part = self.len_lstrip(part[1:])
        offset += 1 + add
        tagname, t_length = self.stack[-1]
        if part[:t_length].lower() != tagname:
            raise BBCodeSyntaxError(offset)
        add, part = self.len_lstrip(part[t_length:])
        offset += t_length + add
        if part[:1] != ']':
            raise BBCodeSyntaxError(offset)

        self.stack.pop()
        offset += 1
        return offset

    def _append_plains(self, nodelist, plains, REGEX_NODES):
        """根据 \n 切分 plains"""
        while plains:
            for name, nodecls in REGEX_NODES.itervalues():
                # 尝试匹配正则表达式成为节点
                m = nodecls.regex.search(plains)
                if not m:
                    continue
                start, stop = m.span()
                if start == stop:
                    raise RuntimeError(
                        'Potential infinite loop detected in '
                        '%s, please check your regular expression.' % repr(nodecls))
                before = plains[:start]
                if before:
                    self._append_plains(nodelist, before, REGEX_NODES)
                nodelist.append(nodecls(m))
                plains = plains[stop:]
                break
            else:
                # 没有任何一次匹配上, 直接作为plain处理
                plains = plains.split('\n')
                nodelist.extend(map(lambda t: PlainNode(t + '\n'), plains[:-1]))
                last = plains[-1]
                if last:
                    nodelist.append(PlainNode(last))
                break
        return nodelist

    def parse(self, source, NODES, REGEX_NODES):
        offset = 0
        remains = ''
        nodelist = []
        while source:
            pos = source.find('[')
            pos = pos if pos > -1 else (len(source) + 1)
            remains += source[:pos]
            source = source[pos:]
            offset += pos
            try:
                if source[1:].lstrip()[:1] == '/':
                    add = self.parse_right(source)
                    if remains:
                        self._append_plains(nodelist, remains, REGEX_NODES)
                        remains = ''
                    # end of the nodelist, jump out
                    offset += add
                    return offset, nodelist
                else:
                    # has nested parse in parse_left
                    add, node = self.parse_left(source, NODES, REGEX_NODES)
                    if remains:
                        self._append_plains(nodelist, remains, REGEX_NODES)
                        remains = ''
                    nodelist.append(node)
            except BBCodeSyntaxError, ex:
                add = ex.args[0]
                remains += source[:add]
            source = source[add:]
            offset += add
        if remains:
            self._append_plains(nodelist, remains, REGEX_NODES)
        return offset, nodelist

    def text(self):
        return self.nodes.text()

    def html(self, **kwargs):
        return self.nodes.html(**kwargs)

    def bbcode(self):
        return unicode(self.nodes)

    @property
    def nodes(self):
        if not hasattr(self, '_top_node'):
            _, nodelist = self.parse(self.source, _NODES, _REGEX_NODES)
            self._top_node = TopNode(None, nodelist)
            self.stack = [] # empty stack whatever
            trigger_hook('after_parse', self)
        return self._top_node

    def __html__(self):
        return self.nodes.html()

    def __unicode__(self):
        return unicode(self.nodes)

    def __str__(self):
        return str(self.nodes)
