from book_web.spiders.novel_parser.BaseParser import BaseParser
from pyquery import PyQuery as pq
from book_web.utils.common_data import BOOK_TYPE_DESC


class BiqudaoParser(BaseParser):
    book_type = BOOK_TYPE_DESC.Novel
    image_base_url = 'https://www.biqudao.com'
    page_base_url = 'https://www.biqudao.com'
    filename_extension = 'jpg'
    request_header = {
        'Accept':
        'text/html,application/xhtml+xm…plication/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding':
        'gzip, deflate, br',
        'Accept-Language':
        'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Cache-Control':
        'no-cache',
        'Connection':
        'keep-alive',
        'Cookie':
        'bookid=174401; chapterid=91595…t=; size=; fontcolor=; width=',
        'DNT':
        "1",
        'Host':
        'www.biqudao.com',
        'Pragma':
        'no-cache',
        'Upgrade-Insecure-Requests':
        "1",
        'referer':
        'https://manhua.dmzj.com/',
        'user-agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36'
    }

    def parse_info(self, data):
        doc = pq(data)
        book_name = doc('#info h1').text()
        book_desc = doc('#intro').text()
        latest_chapter_str = doc('#info a').text()
        # 选取<td>里第1个 a 元素中的文本块
        author_name = doc('#info p').eq(0).text()
        markeup = ""
        cover = doc("#fmimg img").attr('src')

        info = {
            'name': book_name,
            'latest_chapter': latest_chapter_str,
            'desc': book_desc,
            'author_name': author_name,
            'markeup': markeup,
            'cover': self.page_base_url + cover
        }
        return info

    def parse_chapter(self, data):
        doc = pq(data)
        url_list = {}

        for u in doc('#list a'):
            url_list.setdefault(
                pq(u).text(), self.page_base_url + pq(u).attr('href'))

        return (url_list, )

    def parse_chapter_content(self, data):
        doc = pq(data)
        content = doc("#content").text()
        return content

    def parse_chapter_singal(self, data):
        doc = pq(data)
        title = doc(".bookname h1").text()
        content = doc("#content").text()
        return {"title": title, "content": content}
