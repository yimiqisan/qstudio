# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
from werkzeug import html as html_builder
from frame.platform.contribs import bbcode

class BBCodeTestCase(unittest.TestCase):

    def test_unclosed(self):
        bb = bbcode.BBCode("xxx[ul]gdgd\nasfdg")
        # auto correct
        self.assertEqual(bb.nodes.html(), 'xxx' + html_builder.ul(
            html_builder.li('gdgd'),
            html_builder.li('asfdg')))

        # nested unclosed
        bb = bbcode.BBCode("xxx[ul]gdgd\n[ol]asfdg")
        # auto correct
        self.assertEqual(bb.nodes.html(), 'xxx' + html_builder.ul(
            html_builder.li('gdgd'),
            html_builder.li(html_builder.ol(html_builder.li('asfdg')))))

        # wrong closer
        bb = bbcode.BBCode("[ul]aaaa\nbbbb\n[/ol]")
        self.assertEqual(bb.nodes.html(), html_builder.ul(
            html_builder.li('aaaa'),
            html_builder.li('bbbb'),
            html_builder.li('[/ol]')))

    def test_overlapped_nested(self):
        bb = bbcode.BBCode("xxx[bold]aaaaaa[i]dgdgg[/bold]www[/i]yyy")
        self.assertEqual(bb.nodes.html(),
            'xxx<strong>aaaaaa<i>dgdgg[/bold]www</i>yyy</strong>')

    def test_nested(self):
        bb = bbcode.BBCode(
            "[ul]abcdef[ul]ccc\nyyy\n[/ul]ddddd[/ul]adgd")
        self.assertEqual(bb.nodes.html(), html_builder.ul(
            html_builder.li('abcdef', html_builder.ul(
                html_builder.li('ccc'),
                html_builder.li('yyy'))),
            html_builder.li('ddddd')) + 'adgd')

    def test_complex_list(self):
        bb = bbcode.BBCode(
            "[ul]\n"
            "abcde[url=http://g.cn]te\nst[/url]eeff\n" # 内嵌 inline 元素
            "dds\n"
            "[/ul]\n") # 末尾换行
        self.assertEqual(bb.html(), html_builder.ul(
            html_builder.li(
                'abcde',
                html_builder.a('te<br />\nst', href='http://g.cn'),
                'eeff'),
            html_builder.li(
                'dds')) + '\n')

    def test_text(self):
        bb = bbcode.BBCode("xxx[bold]aaaaaa[i]dgdgg[/bold]www[/i]yyy")
        self.assertEqual(bb.text(),
            'xxxaaaaaadgdgg[/bold]wwwyyy')
        bb = bbcode.BBCode("sssss[img]xxxxx[/img]eeeee")
        self.assertEqual(bb.text(), 'ssssseeeee')
        bb = bbcode.BBCode('asdfd[url="http://eefe"][/url]')
        self.assertEqual(bb.text(), 'asdfdhttp://eefe')

    def test_bbcode_correction(self):
        bb = bbcode.BBCode("xxx[ul]gdgd\n[ol]asfdg")
        self.assertEqual(unicode(bb), 'xxx[ul]gdgd\n[ol]asfdg[/ol][/ul]')
        bb = bbcode.BBCode("xxx[bold]aaaaaa[i]dgdgg[/bold]www[/i]yyy")
        self.assertEqual(str(bb), "xxx[bold]aaaaaa[i]dgdgg[/bold]www[/i]yyy[/bold]")

    def test_case_insensitive(self):
        bb = bbcode.BBCode(
            "坑[bold]爹[/BOLD]呢[italic]啊[/italic]!\n")
        self.assertEqual(bb.html(),
            "坑<strong>爹</strong>呢<i>啊</i>!<br />\n")

    def test_br(self):
        bb = bbcode.BBCode("aaaaaa\nbbbbbb\r\ncccccc\r")
        self.assertEqual(bb.nodes.html(),
            "aaaaaa<br />\nbbbbbb<br />\ncccccc<br />\n")

    def test_url(self):
        # 混合测试三种url语法
        bb = bbcode.BBCode(
            "abcd[url]http://inner.com[/url], [url=https://value.com][/url], "
            "[url=https://titled.com]titled[/url]")
        self.assertEqual(bb.nodes.html(),
            "abcd<a href=\"http://inner.com\">http://inner.com</a>, "
            "<a href=\"https://value.com\">https://value.com</a>, "
            "<a href=\"https://titled.com\">titled</a>")
        # xss filter 1
        bb = bbcode.BBCode('[url]javaSCript:alert("xss")[/url]')
        self.assertEqual(bb.nodes.html(),
            "<a href=\"%3C%21--%20XSS%20removed%20--%3E\">javaSCript:alert(\"xss\")</a>")
        # xss filter 2
        bb = bbcode.BBCode('[url]&#106;&#97;vascript:alert("xss")[/url]')
        self.assertEqual(bb.nodes.html(),
            '<a href="&amp;#106;&amp;#97;vascript:alert(&quot;xss&quot;)">'
            '&amp;#106;&amp;#97;vascript:alert("xss")</a>')
        # xss filter 3
        bb = bbcode.BBCode('[url]"><script>alert("xss")</script>[/url]')
        self.assertEqual(bb.nodes.html(),
            '<a href="&quot;%3E%3Cscript%3Ealert(&quot;xss&quot;)'
            '%3C/script%3E">"&gt;&lt;script&gt;alert("xss")&lt;/script'
            '&gt;</a>')
        # url nested
        bb = bbcode.BBCode('[url="http://test.com"][url]fake[/url][/url]')
        self.assertEqual(bb.nodes.html(),
            '<a href="http://test.com">[url]fake</a>[/url]')
        # image nested
        bb = bbcode.BBCode('[url="http://test.com"][image]http://xxx[/image][/url]')
        self.assertEqual(bb.nodes.html(),
            '<a href="http://test.com"><img src="http://xxx" style="max-width: 480px" /></a>')

    def test_color(self):
        bb = bbcode.BBCode('[color=red]xxx[/color]yyy[color=#aaa]zzz[/color]')
        self.assertEqual(bb.nodes.html(),
            '<span style="color: red;">xxx</span>yyy'
            '<span style="color: #aaa;">zzz</span>')
        # xss filter
        bb = bbcode.BBCode('[color="red; backgroud: red;"]xxx[/color]')
        self.assertEqual(bb.nodes.html(),
            '<span style="<!-- XSS removed -->">xxx</span>')

    def test_image(self):
        bb = bbcode.BBCode('[image]http://image[/image]')
        self.assertEqual(bb.nodes.html(),
            '<img src="http://image" style="max-width: 480px" />')
        # invalid syntax
        bb = bbcode.BBCode('[img="http://fake"]xxxx[/img]')
        self.assertEqual(bb.nodes.html(),
            '[img="<a href="http://fake">http://fake</a>"]xxxx[/img]')

    def test_old_image(self):
        bb = bbcode.BBCode('[image]/gkimage/ab/cd/ef/abcdef.jpg[/image]')
        self.assertEqual(bb.nodes.html(),
            '<img src="http://img1.guokr.com/gkimage/ab/cd/ef/abcdef.jpg" style="max-width: 480px" />')
        bb = bbcode.BBCode('[image]http://cms.guokr.com/gkimage/ab/cd/ef/abcdef.jpg[/image]')
        self.assertEqual(bb.nodes.html(),
            '<img src="http://img1.guokr.com/gkimage/ab/cd/ef/abcdef.jpg" style="max-width: 480px" />')

    def test_table(self):
        bb = bbcode.BBCode('[table]\n[tr]\n[td]123[/td]\n[td]abc[/td]\n[/tr]\n[/table]\n')
        self.assertEqual(bb.nodes.html(),
            '<table>\n<tr>\n<td>123</td>\n<td>abc</td>\n</tr>\n</table>\n')

    def test_video(self):
        bb = bbcode.BBCode('[video]http://v.youku.com/v_show/id_XNDg1NzIzNjYw.html[/video]')
        self.assertEqual(bb.html(), html_builder.iframe(
            src='http://player.youku.com/embed/XNDg1NzIzNjYw',
            frameborder=0, allowfullscreen='true',
            width=480, height=400))
        bb = bbcode.BBCode('[video]http://youku.com/fakeurl.swf[/video]')
        self.assertEqual(bb.html(), '[video]<a href="http://youku.com/fakeurl.swf">http://youku.com/fakeurl.swf</a>[/video]')
        bb = bbcode.BBCode('[video]http://player.youku.com/player.php/sid/XNDg1NzIzNjYw/v.swf[/video]')
        self.assertEqual(bb.html(), html_builder.iframe(
            src='http://player.youku.com/embed/XNDg1NzIzNjYw',
            frameborder=0, allowfullscreen='true',
            width=480, height=400))
        # xss filter
        bb = bbcode.BBCode('[video]http://www.tudou.com/fakeurl.swf" src="javascript:alert(\'xss\')[/video]')
        self.assertEqual(bb.html(),
            '<embed src="%s" wmode="transparent" '
            'width="480" quality="high" height="400" '
            'allowscriptaccess="sameDomain" allowfullscreen="true" '
            'type="application/x-shockwave-flash">' %
            'http://www.tudou.com/fakeurl.swf&quot; src=&quot;javascript:alert(\'xss\')')

    def test_ref(self):
        bb = bbcode.BBCode('xx [REF]/article/123465[/REF] yy')
        self.assertEqual(bb.html(),
            'xx <a class="bbcode-ref" href="/article/123465/">/article/123465/</a> yy')
        bb = bbcode.BBCode('xx [ref]http://guo.kr/question/111/[/REF] yy')
        self.assertEqual(bb.html(),
            'xx <a class="bbcode-ref" href="http://guo.kr/question/111/">http://guo.kr/question/111/</a> yy')
        bb = bbcode.BBCode('xx [ref]http://guo.kr/question/111/answer/3333/[/REF] yy')
        self.assertEqual(bb.html(),
            'xx <a class="bbcode-ref" href="http://guo.kr/question/111/answer/3333/">http://guo.kr/question/111/answer/3333/</a> yy')

    def test_flash(self):
        bb = bbcode.BBCode('[flash]http://test.com/fake.swf[/flash]')
        self.assertEqual(bb.html(),
            '<embed src="%s" type="application/x-shockwave-flash" '
            'allowscriptaccess="sameDomain" allowfullscreen="true" '
            'wmode="transparent" quality="high" width="480" height="400">'
            '</embed>' % 'http://test.com/fake.swf')
        # xss filter 1
        bb = bbcode.BBCode('[flash]javascript:alert(\\"xss\\")[/flash]')
        self.assertEqual(bb.html(),
            '<embed src="%s" type="application/x-shockwave-flash" '
            'allowscriptaccess="sameDomain" allowfullscreen="true" '
            'wmode="transparent" quality="high" width="480" height="400">'
            '</embed>' % '%3C%21--%20XSS%20removed%20--%3E')
        # xss filter
        bb = bbcode.BBCode('[flash]http://test.com/fakeurl.swf" src="javascript:alert(\'xss\')[/flash]')
        self.maxDiff=30000
        self.assertEqual(bb.html(),
            '<embed src="%s" type="application/x-shockwave-flash" '
            'allowscriptaccess="sameDomain" allowfullscreen="true" '
            'wmode="transparent" quality="high" width="480" height="400">'
            '</embed>' % 'http://test.com/fakeurl.swf&quot;%20src=&quot;javascript:alert(%27xss%27)')

    def test_maximum_depth(self):
        bb = bbcode.BBCode('[ul][ol]' * 128 + 'xx')
        self.assertEqual(bb.html(),
            '<ul><li><ol><li>' * 128 + 'xx' + '</li></ol></li></ul>' * 128)
        # overflowed
        bb = bbcode.BBCode('[ul][ol]' * 129 + 'xx')
        self.assertEqual(bb.html(),
            '<ul><li><ol><li>' * 128 + '[ul][ol]xx' + '</li></ol></li></ul>' * 128)

    def test_at_and_email(self):
        bb = bbcode.BBCode(u'这件事要请教@天蓝提琴 一下')
        self.assertEqual(bb.html(), u'这件事要请教<a href="#">@天蓝提琴</a> 一下')
        # email like at
        bb = bbcode.BBCode(u'man@sela')
        self.assertEqual(bb.html(), u'man<a href="#">@sela</a>')
        # email
        bb = bbcode.BBCode(u'求种！邮箱：diaosi@gmail.com')
        self.assertEqual(bb.html(), u'求种！邮箱：<a href="mailto:diaosi@gmail.com">diaosi@gmail.com</a>')
        # url contains at
        bb = bbcode.BBCode(u'[url="http://guo.kr"]我@不到用户[/url]，@果壳网孙小年')
        self.assertEqual(bb.html(), u'<a href="http://guo.kr">我@不到用户</a>，<a href="#">@果壳网孙小年</a>')

    def test_regex_url(self):
        bb = bbcode.BBCode(u'访问一下https://zh.wikipedia.org/wiki/果壳网（没骗你）')
        self.assertEqual(bb.html(), u'访问一下<a href="https://zh.wikipedia.org/wiki/%E6%9E%9C%E5%A3%B3%E7%BD%91">https://zh.wikipedia.org/wiki/果壳网</a>（没骗你）')

    def test_filter(self):
        bb = bbcode.BBCode(u'[b]这件事[i]要请教@天蓝提琴 一[/i]下, 是吧@有点儿欢乐 [/b]，@果壳网孙小年')
        at = bb.filter('__at__')
        self.assertEqual(len(at), 3)
        self.assertEqual(at[0].nickname, u'天蓝提琴')
        self.assertEqual(at[1].nickname, u'有点儿欢乐')
        self.assertEqual(at[2].nickname, u'果壳网孙小年')

        at = bb('b i __at__')
        self.assertEqual(len(at), 1)
        self.assertEqual(at[0].nickname, u'天蓝提琴')

        at = bb.filter('quote __at__')
        self.assertEqual(len(at), 0)
