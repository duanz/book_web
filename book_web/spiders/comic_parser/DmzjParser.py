from book_web.spiders.comic_parser.BaseParser import BaseParser
from pyquery import PyQuery as pq
from book_web.utils import spider_utils as utils
import json
import re
import urllib


class DmzjParser(BaseParser):
    image_base_url = 'https://images.dmzj.com'
    page_base_url = 'https://manhua.dmzj.com'
    filename_extension = 'jpg'
    request_header = {
        'referer':
        'https://manhua.dmzj.com/',
        'user-agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36'
    }

    def parse_info(self, data):
        doc = pq(data)
        '.comic_deCon > h1:nth-child(1) > a:nth-child(1)'
        comic_name = doc('.anim_title_text h1').text()
        comic_desc = doc('div.line_height_content').text()
        latest_chapter_str = doc('#newest_chapter').text()
        latest_chapter = int(
            re.search(r"\d+", latest_chapter_str).group() or 0)
        # 选取<td>里第1个 a 元素中的文本块
        author_name = doc('.anim-main_list td a').eq(0).text()
        markeup = doc('.anim-main_list td').eq(6)('a').text()
        cover = doc("#cover_pic").attr('src')

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
        doc = pq(data)
        url_list = {}

        for u in doc('.cartoon_online_border ul li a'):
            url_list.setdefault(
                pq(u).text(), self.page_base_url + pq(u).attr('href'))

        return (url_list, )

    def parse_image_list(self, data):
        jspacker_string = re.search(r'(eval\(.+\))', data).group()
        jspacker_string = utils.decode_packed_codes(jspacker_string)

        image_list = re.search(r'(\[.+\])', jspacker_string).group()
        image_list = urllib.parse.unquote(image_list).replace('\\', '')
        image_list = json.loads(image_list)

        images = {}

        for k in image_list:
            images.setdefault(
                k.split('/')[-1].split('.')[0], self.image_base_url + '/' + k)
        return images
