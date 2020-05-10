from __future__ import absolute_import, unicode_literals
from pyquery import PyQuery as pq
from book_web.utils.common_data import BOOK_TYPE_DESC
import json
import re
import urllib
from book_web.utils import spider_utils as utils
from book_web.spiders.comic_parser.BaseParser import BaseParser


class ComDmzjParser(BaseParser):
    book_type = BOOK_TYPE_DESC.Comic
    encoding = 'UTF-8'

    image_base_url = 'https://images.dmzj.com'
    page_base_url = 'https://www.dmzj.com'
    filename_extension = 'jpg'
    request_header = {
        "Accept-Language":
        "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Accept-Encoding":
        "gzip, deflate, br",
        "Connection":
        "keep-alive",
        "If-None-Match":
        "3476fb1b07f805d65571ba1427893aad",
        "Cache-Control":
        "max-age=0",
        "referer":
        "https://www.dmzj.com/",
        "user-agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36"
    }
    cookie_str = "show_tip_1=0; pt_s_198bb240=vt=1584176879286&cad=; pt_198bb240=uid=rtAfcatLuC88ZZD9dqbWjw&nid=0&vid=T-5uM0RkfOSaHqgfHpmFOA&vn=6&pvn=1&sact=1584199925402&to_flag=0&pl=J8gHIAMoYA2Eg1lD2m4zWQ*pt*1584199925402; display_mode=0; pic_style=0; setUp=0"
    cookie_dict = {
        i.split("=")[0]: i.split("=")[-1]
        for i in cookie_str.split("; ")
    }

    def parse_info(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)
        doc = pq(data)

        comic_name = doc(
            '.comic_deCon > h1:nth-child(1) > a:nth-child(1)').text()
        comic_desc = doc('.comic_deCon_d').text()
        latest_chapter_str = doc('#newest_chapter').text()
        latest_chapter = int(re.search(
            r"\d+", latest_chapter_str).group()) if re.search(
                r"\d+", latest_chapter_str) else 0
        # 选取<td>里第1个 a 元素中的文本块
        author_name = doc('.comic_deCon_liO > li:nth-child(1)').text()
        markeup = ""
        cover = doc(".comic_i_img > a:nth-child(1) > img:nth-child(1)").attr(
            'src')
        if not isinstance(cover, list):
            cover = [cover]

        info = {
            'name': comic_name,
            'latest_chapter': latest_chapter,
            'desc': comic_desc,
            'author_name': author_name,
            'markeup': markeup,
            'cover': cover
        }
        return info

    def parse_chapter(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)

        doc = pq(data)
        chapter_list = []

        for u in doc('div.tab-content:nth-child(3) > ul:nth-child(1) > li'):
            name = u.find_class('list_con_zj')[0].text if u.find_class(
                'list_con_zj') and hasattr(
                    u.find_class('list_con_zj')[0], 'text') else None
            href = u.find('a').get('href')
            if not name or not href:
                raise Exception(
                    'parse chapter list error: name: {}, href: {}'.format(
                        name, href))
            chapter_list.append({name: href})
        chapter_list.reverse()
        return chapter_list

    def parse_image_list(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)
        # data = data.text if hasattr(data, 'text') else data

        jspacker_string = re.search(r'(eval(.+))', data).group()
        jspacker_string = utils.decode_packed_codes(jspacker_string)
        jspacker_string = eval(
            repr(jspacker_string).replace('\\\\\\\\', '\\').replace(
                '\\/', '/').replace('\\r\\n', ','))
        jspacker_dict = eval(re.search("{.+}",
                                       jspacker_string).group()) if re.search(
                                           "{.+}", jspacker_string) else {}
        image_list = []
        if jspacker_dict and "page_url" in jspacker_dict and jspacker_dict[
                "page_url"]:
            page_url = jspacker_dict.get("page_url", "")
            image_list = page_url.split(",")

        images = {}
        for k in image_list:
            try:
                index = int(k.split('/')[-1].split('.')[0])
            except ValueError:
                index = -1
            images.setdefault(index, self.image_base_url + '/' + k)
        return images

    def parse_chapter_content(self, data):
        content = self.parse_image_list(data)
        return content

    def parse_chapter_singal(self, data):
        title, content = self.get_content_info(data)
        return {"title": title, "content": content}
