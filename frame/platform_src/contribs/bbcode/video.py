# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""处理 video 标签"""

import re
import time
import json
import base64
from werkzeug import html as html_builder

from guokr.platform import urlfetch
from guokr.platform.engines import _share_redis

from .core import register_node, BaseNode, NodeError

class URLNotMatch(NodeError):
    pass


def render_embed(src, **kwargs):
    width = kwargs.get('resp_width', 480)
    height = width * 5 / 6
    return html_builder.embed(
        src=src,
        type='application/x-shockwave-flash',
        allowscriptaccess='sameDomain',
        allowfullscreen='true', wmode='transparent',
        quality='high', width=width, height=height)


def render_iframe(src, **kwargs):
    width = kwargs.get('resp_width', 480)
    height = width * 5 / 6
    return html_builder.iframe(
        src=src,
        frameborder=0,
        allowfullscreen='true',
        width=width, height=height)


class _SiteAdapter(object):

    def __init__(self, url):
        self.url = url
        self.renderer = self.init(url)

    def init(self, url):
        raise NotImplementedError

    def __call__(self, **kwargs):
        return self.renderer(**kwargs)


class _IframeAdapter(_SiteAdapter):

    _regex = None
    _srctpl = None

    def kw_handler(self, kw):
        return kw

    def init(self, url):
        if not self._regex or not self._srctpl:
            raise NotImplementedError
        regex = self._regex
        if not isinstance(regex, (list, tuple)):
            regex = [regex]
        for p in regex:
            m = p.search(url)
            if not m:
                continue
            src = self._srctpl % self.kw_handler(m.groupdict())
            return lambda **kwargs: render_iframe(src, **kwargs)
        else:
            raise URLNotMatch()


class _FlashAdapter(_SiteAdapter):

    _regex = None
    _srctpl = None

    def kw_handler(self, kw):
        return kw

    def init(self, url):
        if not self._regex or not self._srctpl:
            raise NotImplementedError
        regex = self._regex
        if not isinstance(regex, (list, tuple)):
            regex = [regex]
        for p in regex:
            m = p.search(url)
            if not m:
                continue
            src = self._srctpl % self.kw_handler(m.groupdict())
            return lambda **kwargs: render_embed(src, **kwargs)
        else:
            raise URLNotMatch()


class YoukuAdapter(_IframeAdapter):
    """优酷网HTML5"""

    # 优酷的 id 模式: X<b64encoded id>
    _regex = [
        re.compile(r'^http://v\.youku\.com/v_show/id_(?P<id>X[\w=-]+)\.html'),
        re.compile(r'^http://player\.youku\.com/player\.php/+(?:.+?/)?sid/(?P<id>X[\w=-]+)/v\.swf'),
        re.compile(r'^http://player\.youku\.com/embed/(?P<id>X[\w=-]+)'),
    ]
    _srctpl = 'http://player.youku.com/embed/%(id)s'


class TudouAdapter(_IframeAdapter):
    """土豆网HTML5"""

    _regex = [
        re.compile(r'^http://(?:www\.)?tudou\.com/programs/view/(?P<id>[\w-]+)/'),
        re.compile(r'^http://(?:www\.)?tudou\.com/programs/view/html5embed\.action\?code=(?P<id>[\w-]+)'),
        re.compile(r'^http://(?:www\.)?tudou\.com/(?:listplay|albumplay)/(?:[\w-]+)/(?P<id>[\w-]+)\.html'),
        re.compile(r'^http://(?:www\.)?tudou\.com/v/(?P<id>[\w-]+)/v\.swf'),
    ]
    _srctpl = 'http://www.tudou.com/programs/view/html5embed.action?code=%(id)s'


class Ku6Adapter(_FlashAdapter):
    """酷6网"""

    _regex = [
        re.compile(r'^http://v\.ku6\.com/show/(?P<id>[\w\.-]+)\.html'),
        re.compile(r'^http://player\.ku6\.com/refer/(?P<id>[\w\.-]+)/v\.swf'),
    ]
    _srctpl = 'http://player.ku6.com/refer/%(id)s/v.swf'


class W56Adapter(_IframeAdapter):
    """56网HTML5"""

    _regex = [
        re.compile(r'^http://(?:www\.)?56\.com/(?:u\d+/v_|w\d+/play_album-aid-\d+_vid-)(?P<id>[\w=-]+)\.html'),
        re.compile(r'^http://player\.56\.com/v_(?P<id>[\w=-]+)\.swf'),
        re.compile(r'^http://(?:www\.)?56\.com/iframe/(?P<id>[\w=-]+)'),
    ]
    _srctpl = 'http://www.56.com/iframe/%(id)s'


class W56PicAdapter(_FlashAdapter):
    """56网图片"""

    _regex = [
        re.compile(r'^http://(?:www\.)?56\.com/p\d+/v_(?P<id_b64decode>v_[\w=-]+)\.html'),
        re.compile(r'^http://player\.56\.com/deux_(?P<id>v_[\w=-]+)\.swf'),
    ]
    _srctpl = 'http://player.56.com/deux_%(id)s.swf'

    def kw_handler(self, kw):
        if 'id' not in kw:
            kw['id'] = base64.urlsafe_b64decode(kw.pop('id_b64decode'))
        return kw


class QQAdapter(_FlashAdapter):
    """腾讯视频"""

    _regex = [
        re.compile(r'^http://v\.qq\.com/cover/./[\w=-]+\.html\?vid=(?P<id>[\w=-]+)'),
        re.compile(r'^http://v\.qq\.com/cover/./[\w=-]+/(?P<id>[\w=-]+)\.html'),
        re.compile(r'^http://v\.qq\.com/page/./././(?P<id>[\w=-]+)\.html'),
        re.compile(r'^http://static\.video\.qq\.com/TPout\.swf\?vid=(?P<id>[\w=-]+)'),
    ]
    _srctpl = 'http://static.video.qq.com/TPout.swf?vid=%(id)s&auto=0'


class SinaAdapter(_FlashAdapter):
    """新浪视频"""

    _regex = [
        re.compile(r'^http://video\.sina\.com\.cn/v/b/(?P<vid>\d+)-(?P<uid>\d+)\.html'),
        re.compile(r'^http://video\.weibo\.com/v/weishipin/(?P<mix_vid>[\w-]+).htm'),
        re.compile(r'^http://you\.video\.sina\.com\.cn/api/sinawebApi/outplayrefer\.php/vid=(?P<vid>\d+)_(?P<uid>\d+)'),
    ]
    _page_regex = _regex[0]
    _srctpl = 'http://you.video.sina.com.cn/api/sinawebApi/outplayrefer.php/vid=%(vid)s_%(uid)s/s.swf'

    def kw_handler(self, kw):
        if 'vid' in kw and 'uid' in kw:
            return kw

        elif 'mix_vid' in kw:
            mix_vid = kw.pop('mix_vid')
            cache = _share_redis.hget('bbcode-video-weibo-url', mix_vid)
            try:
                kw['vid'], kw['uid'] = json.loads(cache)
                return kw
            except (ValueError, TypeError):
                pass

            try:
                resp = urlfetch.get(
                    'http://video.weibo.com/',
                    params={
                        's': 'v',
                        'a': 'play_list',
                        'format': 'json',
                        'mix_video_id': mix_vid,
                        'date': int(time.time() * 1000),
                        'for': ''
                    })
            except KeyboardInterrupt:
                raise
            except:
                raise URLNotMatch()
            if resp.status_code != 200:
                raise URLNotMatch()
            try:
                page = resp.json['result']['data'][0]['play_page_url']
                m = self._page_regex.search(page)
            except (KeyError, TypeError):
                raise URLNotMatch()
            if not m:
                raise URLNotMatch()
            kw.update(m.groupdict())
            _share_redis.hset('bbcode-video-weibo-url', mix_vid, json.dumps([kw['vid'], kw['uid']]))
            return kw


class SohuAdapter(_FlashAdapter):
    """搜狐视频"""

    _regex = [
        re.compile(r'^http://share\.vrs\.sohu\.com/(?P<id>\d+)/v\.swf'),
        re.compile(r'^(?P<url>http://tv\.sohu\.com/\d+/n\d+\.shtml)'),
    ]
    _swf_regex = _regex[0]

    # XXX: 没错, sohu 用的是 & 而不是 ?
    _srctpl = 'http://share.vrs.sohu.com/%(id)s/v.swf&autoplay=false'

    def kw_handler(self, kw):
        if 'id' in kw:
            return kw

        url = kw.pop('url')
        vid = _share_redis.hget('bbcode-sohu-url', url)
        if vid:
            kw['id'] = vid
            return kw

        try:
            resp = urlfetch.post(
                'http://open.tv.sohu.com/tools/flash/url/get.do',
                data={'url': url})
        except KeyboardInterrupt:
            raise
        except:
            raise URLNotMatch()
        if resp.status_code != 200:
            raise URLNotMatch()
        try:
            flash = resp.json['flash']
            m = self._swf_regex.search(flash)
        except (KeyError, TypeError):
            raise URLNotMatch()
        if not m:
            raise URLNotMatch()
        kw['id'] = vid = int(m.group('id'))
        _share_redis.hset('bbcode-sohu-url', url, vid)
        return kw


class Open163Adapter(_FlashAdapter):
    """网易公开课"""

    _regex = [
        re.compile(r'^http://v\.163\.com/movie/\d{4}/\d{1,2}/[A-Z\d]/[A-Z\d]/(?P<id>[A-Z\d]+_[A-Z\d]+).html'),
        re.compile(r'^http://swf\.ws\.126\.net/openplayer/v01/-0-2_(?P<id>[A-Z\d]+_[A-Z\d]+)-'),
    ]
    _srctpl = 'http://swf.ws.126.net/openplayer/v01/-0-2_%(id)s-.swf'


class NeteaseAdapter(_FlashAdapter):
    """网易视频"""

    _regex = [
        re.compile(r'^http://v\.163\.com/(?P<vtype>[^/]+)/(?P<sid>[A-Z\d]+)/(?P<vid>[A-Z\d]+)\.html'),
        re.compile(r'^http://swf\.ws\.126\.net/v/ljk/shareplayer/ShareFlvPlayer\.swf\?pltype=(?P<pltype>\d+)&topicid=(?P<topicid>\d+)&vid=(?P<vid>[A-Z\d]+)&sid=(?P<sid>[A-Z\d]+)'),
    ]
    _srctpl = 'http://swf.ws.126.net/v/ljk/shareplayer/ShareFlvPlayer.swf?pltype=%(pltype)s&topicid=%(topicid)s&vid=%(vid)s&sid=%(sid)s&autoplay=false'

    _typemap = {
        'zongyi': ('4', '0085'),
        'jishi': ('5', '0085'),
        'zixun': ('6', '0085'),
        'yule': ('8', '0085'),
        'mv': ('9', '0085'),
        'paike': ('10', '1000'),
    }

    def kw_handler(self, kw):
        if 'pltype' in kw:
            return kw

        try:
            kw['pltype'], kw['topicid'] = self._typemap[kw.pop('vtype')]
        except KeyError:
            raise URLNotMatch()

        return kw


class LetvAdapter(_FlashAdapter):
    """乐视网"""

    _regex = [
        re.compile(r'^http://www\.letv\.com/ptv/vplay/(?P<id>\d+)\.html'),
        re.compile(r'^http://(i7\.imgs|img1\.c0)\.letv\.com/.+?/swfPlayer\.swf\?.*?id=(?P<id>\d+)')
    ]
    _srctpl = 'http://i7.imgs.letv.com/player/swfPlayer.swf?id=%(id)s&autoplay=0'


class AcfunAdapter(_FlashAdapter):
    """Acfun弹幕网"""

    _regex = [
        re.compile(r'^(?P<id>http://www\.acfun\.tv/v/ac\d+)'),
        re.compile(r'^http://cdn\.acfun\.tv/player/ACFlashPlayer\.weibo2\.swf\?type=page&url=(?P<id>[^\&]+)'),
    ]
    _srctpl = 'http://cdn.acfun.tv/player/ACFlashPlayer.weibo2.swf?type=page&url=%(id)s'


class BilibiliAdapter(_FlashAdapter):
    """Bilibili弹幕网"""

    _regex = [
        re.compile(r'^http://www\.bilibili\.tv/video/av(?P<id>\d+)(?:/index_(?P<page>\d+))?'),
        re.compile(r'^http://static\.hdslb\.com/miniloader\.swf\?aid=(?P<id>\d+)(?:&page=(?P<page>\d+))?'),
    ]
    _srctpl = 'http://static.hdslb.com/miniloader.swf?aid=%(id)s&page=%(page)s'

    def kw_handler(self, kw):
        if kw.get('page') is None:
            kw['page'] = 1
        return kw


class WhitelistFlashAdapter(_FlashAdapter):

    _regex = re.compile(r'^(?P<url>https?://(?:player\.youku\.com|www\.tudou\.com|'
                        r'player\.ku6\.com|player\.56\.com|'
                        r'share\.vrs\.sohu\.com|\w+\.video\.sina\.com\.cn|'
                        r'\w+\.video\.qq\.com|swf\.ws\.126\.net|'
                        r'player\.cntv\.cn|'
                        r'union\.bokecc\.com|\w+\.video\.qiyi\.com)/.+)$')
    _srctpl = '%(url)s'


@register_node('video')
class VideoNode(BaseNode):
    name = 'video'
    #display = 'block'
    tag_includes = []

    adapters = [
        YoukuAdapter,
        TudouAdapter,
        Ku6Adapter,
        W56Adapter,
        W56PicAdapter,
        QQAdapter,
        SinaAdapter,
        SohuAdapter,
        Open163Adapter,
        NeteaseAdapter,
        LetvAdapter,
        AcfunAdapter,
        BilibiliAdapter,
        WhitelistFlashAdapter
    ]

    def __init__(self, value, children):
        super(VideoNode, self).__init__(value, children)
        url = self.children_unicode().strip()
        for adapter in self.adapters:
            try:
                self.renderer = adapter(url)
                break
            except URLNotMatch:
                continue
        else:
            raise NodeError('Invalid video URL')

    def text(self):
        return ''

    def html(self, **kwargs):
        return self.renderer(**kwargs)
