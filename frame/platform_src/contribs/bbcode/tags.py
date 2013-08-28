# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from flask import current_app as app
from pkg_resources import parse_version as V
from werkzeug import escape, unescape, url_quote, html as html_builder
from .core import register_node, register_hook, BaseNode, \
    PlainNode, RegexNode, NodeError

URL_QUOTE_SAFE = b'/:;"%&#()=?'


class _ListNode(BaseNode):
    display = 'block'
    list_builder = None

    def html(self, **kwargs):
        children = []
        innerhtml = ''

        def append_li(html):
            html = html.strip()
            if html:
                children.append(html_builder.li(html))
            return ''

        for node in self.children:
            if not node:
                continue
            if isinstance(node, PlainNode):
                innerhtml += node.html(**dict(kwargs, br=False))  # 此处不出现br
                if node.has_linebreak:
                    # 发现有换行符的纯文本, li 结束
                    innerhtml = append_li(innerhtml)
            else:
                innerhtml += node.html(**kwargs)
                if node.display == 'block':
                    # 发现块级元素, li 结束
                    innerhtml = append_li(innerhtml)

        # 处理循环中没有处理的残留 innerhtml
        append_li(innerhtml)
        # html_builder 返回的函数只能用一次
        return getattr(html_builder, self.html_tagname)(*children)


@register_node('ul')
class UlNode(_ListNode):
    name = 'ul'
    html_tagname = 'ul'


@register_node('ol')
class OlNode(_ListNode):
    name = 'ol'
    html_tagname = 'ol'


@register_node('url')
class URLNode(BaseNode):
    name = 'url'
    tag_excludes = ['url', '__at__', '__email__', '__url__']

    def __init__(self, value, children):
        if not value and not children:
            raise NodeError('URL must contains either value or children')
        if not children:
            children = [PlainNode(value)]
        super(URLNode, self).__init__(value, children)
        url = self.value if self.value else self.children_unicode()
        if url.lower()[:11] == 'javascript:':
            url = '<!-- XSS removed -->'
        self.url = url

    def html(self, **kwargs):
        inside = self.children_html(**kwargs)
        return '<a href="%s">%s</a>' % (
            escape(url_quote(self.url, safe=URL_QUOTE_SAFE), quote=True),
            inside)


@register_node('image', 'img')
class ImageNode(BaseNode):
    name = 'image'
    tag_includes = []

    def __init__(self, value, children):
        if value or not children:
            raise NodeError('Image URL can only be specified from children')
        super(ImageNode, self).__init__(value, children)
        url = self.children_unicode()
        if url.lower()[:11] == 'javascript:' or \
           url.lower()[:9] == 'vbscript:':
            url = '<!-- XSS removed -->'
        self.url = url

    def text(self):
        return ''

    def html(self, **kwargs):
        from guokr.platform.flask.helpers import resp_image
        from guokr.platform.flask.helpers import get_params, url2hashkey
        width = kwargs.get('resp_width', 480)
        url = resp_image(self.url, width)
        hashkey = url2hashkey(self.url, take_thumbnail=True)
        if not hashkey:
            return '<img src="%s" style="max-width: %spx" />' % (
                escape(url_quote(url, safe=URL_QUOTE_SAFE), quote=True), width)

        w, h, file_type = get_params(hashkey)
        return ('<img src="%s" style="max-width: %spx" '
                'data-orig-width="%s" '
                'data-orig-height="%s" '
                'data-hashkey="%s"/>') % (
                    escape(url_quote(url, safe=URL_QUOTE_SAFE), quote=True),
                    width,
                    w,
                    h,
                    hashkey)


@register_node('bold', 'b')
class BoldNode(BaseNode):
    name = 'bold'
    tag_excludes = ['bold', 'b']

    def html(self, **kwargs):
        if not self.children:
            return ''
        else:
            return '<strong>%s</strong>' % self.children_html(**kwargs)


@register_node('italic', 'i')
class ItalicNode(BaseNode):
    name = 'italic'
    tag_excludes = ['italic', 'i']

    def html(self, **kwargs):
        if not self.children:
            return ''
        else:
            return '<i>%s</i>' % self.children_html(**kwargs)


@register_node('color')
class ColorNode(BaseNode):
    name = 'color'
    tag_excludes = ['color']
    html_colors = re.compile('^([A-Za-z]+|#[0-9A-Fa-f]{,6})$')

    def html(self, **kwargs):
        if not self.children:
            return ''
        if self.value:  # 添加这个，判断无参数的情况
            color = self.value.strip()
        else:
            color = '#000000'  # 默认为白
        if not self.html_colors.match(color):
            style = '<!-- XSS removed -->'
        else:
            style = 'color: ' + color + ';'
        # 偷懒, 没有支持不带 # 的 16 进制写法
        return '<span style="%s">%s</span>' % (
            style, self.children_html(**kwargs))


@register_node('quote', 'blockquote')
class QuoteNode(BaseNode):
    name = 'quote'
    display = 'block'
    tag_excludes = ['quote', 'blockquote']

    def html(self, **kwargs):
        return '<blockquote>%s</blockquote>' % self.children_html(**kwargs)


@register_node('code')
class CodeNode(BaseNode):
    name = 'code'
    tag_excludes = ['code']

    def html(self, **kwargs):
        return '<pre>%s</pre>' % self.children_html(**dict(kwargs, br=False))


@register_node('table', 'th', 'tr')
class TableNode(BaseNode):
    name = 'table'
    display = 'block'

    def html(self, **kwargs):
        innerhtml = []
        for child in self.children:
            if isinstance(child, PlainNode):
                innerhtml.append(child.html(**dict(kwargs, br=False)))
            else:
                innerhtml.append(child.html(**kwargs))
        return getattr(html_builder, self.name)(*innerhtml)


@register_node('_html', 'td', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6')
class HTMLNode(BaseNode):
    name = 'td'
    display = 'block'

    def html(self, **kwargs):
        return getattr(html_builder, self.name)(self.children_html(**kwargs))


@register_node('ref')
class RefNode(BaseNode):
    name = 'ref'
    tag_includes = []

    url_whitelist = re.compile(
        r'^(?:http://(?:(?:www)?\.guokr\.com|guo\.kr))?'
        r'(?P<url>/(?:article|blog|question|answer|post)/\d+|'
        r'/question/\d+/answer/\d+)/?(?:\?|$)')

    def __init__(self, value, children):
        if value or not children:
            raise NodeError('Ref URL can only be specified from children')
        super(RefNode, self).__init__(value, children)
        url = self.children_unicode().strip()
        m = self.url_whitelist.search(url)
        if m:
            self.url = url.rstrip('/') + '/'
        else:
            raise NodeError('Invalid ref URL')

    def html(self, **kwargs):
        return html_builder.a(self.url, href=self.url, class_='bbcode-ref')


@register_node('flash')
class FlashNode(BaseNode):
    name = 'flash'
    tag_includes = []

    def __init__(self, value, children):
        if value or not children:
            raise NodeError('Ref URL can only be specified from children')
        super(FlashNode, self).__init__(value, children)
        url = self.children_unicode().strip()
        if url.lower()[:11] == 'javascript:':
            url = '<!-- XSS removed -->'
        self.url = url

    def html(self, **kwargs):
        width = kwargs.get('resp_width', 480)
        height = width * 5 / 6
        # TODO: use placeholder
        return \
            '<embed src="%s" type="application/x-shockwave-flash" ' \
            'allowscriptaccess="sameDomain" allowfullscreen="true" ' \
            'wmode="transparent" quality="high" width="%s" ' \
            'height="%s"></embed>' % (
                escape(url_quote(self.url, safe=URL_QUOTE_SAFE), quote=True),
                width, height)


@register_node('__url__', weight=100)
class RegexURLNode(RegexNode):
    name = '__url__'
    regex = re.compile(r"""(?iux)
                           (?:https?|ftps?|ssh|sftp|ed2k|git|svn|svn\+ssh|smb)
                           ://[\w\?\.=&+%/#;@:~!,()-]+""")

    @property
    def url(self):
        return self.value.group(0)

    def html(self, **kwargs):
        return '<a href="%s">%s</a>' % (
            escape(url_quote(self.url, safe=URL_QUOTE_SAFE), quote=True),
            escape(self.url))


@register_node('__at__', weight=30)
class AtNode(RegexNode):
    name = '__at__'
    regex = re.compile(r"""(?ux)(?<!@) # 反向否定预查, @@xxx 不是合法的@标签
                           @(?P<nickname>
                               [\w\u3400-\u4db5\u4e00-\u9fcb\.-]{1,20}
                           )""")

    @property
    def nickname(self):
        return self.value.group('nickname')

    def html(self, **kwargs):
        from flask import url_for
        nickname = self.value.group('nickname')
        if app:
            return '<a href="%s">@%s</a>' % (
                url_for(
                    'community:profile.nickname_redirect', nickname=nickname),
                escape(nickname))
        else:
            return '<a href="#">@%s</a>' % escape(nickname)


@register_node('__email__', weight=80)
class EmailNode(RegexNode):
    name = '__email__'
    regex = re.compile(r'(?i)[\w+\.-]+@[\w][\w\.-]*\.[a-z]{2,10}')

    @property
    def email(self):
        return self.value.group(0)

    def html(self, **kwargs):
        return '<a href="mailto:%s">%s</a>' % (
            escape(self.email, quote=True),
            escape(self.email))


@register_node('math')
class MathMode(BaseNode):
    name = 'math'
    tag_includes = []

    @property
    def math(self):
        ret = ''
        for node in self.children:
            if node:
                ret += node.html(br=False)
        return unescape(ret)

    @property
    def hashed(self):
        import hashlib
        return hashlib.sha1(self.math).hexdigest()

    @property
    def format(self):
        from flask import request
        browser = request.user_agent.browser
        version = V(request.user_agent.version or '')
        # version = float('.'.join(version.split('.', 2)[:2])) if version else
        # None
        if not browser or not version:
            return 'png'
        if (
            (browser == 'msie' and version >= V('9')) or  # trident >= 5.0
            (browser == 'firefox' and version >= V('4')) or  # gecko >= 2.0
            (browser == 'webkit' and version >= V('522')) or  # webkit >= 522
            browser == 'chrome' or browser == 'konqueror' or  # all versions
            (browser == 'safari' and version >= V('3.0')) or  # webkit >= 522
                (browser == 'opera' and version > V('9.5'))):  # presto >= 2.1
            return 'svg'
        else:
            return 'png'

    def html(self, **kwargs):
        from flask import url_for
        width = kwargs.get('resp_width', 480)

        return ('<img src="%s" class="edui-faked-insertmathjax"'
                ' data-code="%s" style="max-width: %spx" />') % (
                    url_for(
                        'image:formula',
                        hashed=self.hashed,
                        format=self.format),
                    escape(self.math, quote=True), width)

    def text(self):
        return ''


@register_node('indent')
class IndentNode(BaseNode):

    """缩进标签的显示"""
    name = 'indent'
    display = 'block'

    def html(self, **kwargs):
        if not self.children:
            return ''
        return html_builder.div(self.children_html(**dict(kwargs, br=False)),
                                class_="bbcode-indent")


@register_node('float')
class FloatNode(BaseNode):

    """浮动标签的支持"""
    name = 'float'
    display = 'block'
    tag_excludes = ['float']
    html_float = re.compile('^left|right$')

    def html(self, **kwargs):
        if not self.children:
            return ''
        if self.value:  # 判断是否有参数，不判断会有AttributeError生成
            direction = self.value.strip()
        else:
            direction = 'left'  # 默认左浮
        if not self.html_float.match(direction):
            style = '<!-- XSS removed -->'
        else:
            style = 'bbcode-float-' + direction
        return html_builder.div(self.children_html(**dict(kwargs, br=False)),
                                class_=style)


@register_hook('after_parse')
def math_hook(bbcode):
    from guokr.platform.apis import APIServerError, APIClientError
    from guokr.platform.apis.confidential import formula
    from guokr.platform.engines import _share_redis
    math_map = {}
    for node in bbcode.filter('math'):
        math_map[node.hashed] = node.math
    if not math_map:
        return
    hashed = math_map.keys()
    # 通过redis检查公式是否已经生成过
    result = _share_redis.hmget('image-formula', hashed)
    math_exist = zip(hashed, result)
    for hashed, is_exist in math_exist:
        if is_exist is None:
            # 同步创建, 确保正常显示
            # 生成公式是重操作, 所以单独请求避免造成过大负载
            try:
                formula.create(tex=math_map[hashed], confirm=True)
            except (APIServerError, APIClientError):
                pass
