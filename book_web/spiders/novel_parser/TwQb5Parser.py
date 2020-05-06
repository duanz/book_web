from book_web.spiders.novel_parser.BaseParser import BaseParser
from pyquery import PyQuery as pq


class TwQb5Parser(BaseParser):
    encoding = 'gbk'
    image_base_url = 'https://www.qb5.tw'
    page_base_url = 'https://www.qb5.tw'
    filename_extension = 'jpg'
    request_header = {
        'Accept':
        'text/html,application/xhtml+xm…plication/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding':
        'gzip, deflate, br',
        'Cache-Control':
        'no-cache',
        'Connection':
        'keep-alive',
        'Host':
        'www.biquge.tv',
        'Pragma':
        'no-cache',
        'Upgrade-Insecure-Requests':
        "1",
        'referer':
        'www.biquge.tv',
        'user-agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36  \
            (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36'
    }

    def parse_info(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)

        doc = pq(data)
        book_name = doc('meta[property="og:title"]').attr('content')
        book_desc = doc('meta[property="og:description"]').attr('content')
        latest_chapter_str = doc(
            'meta[property="og:novel:latest_chapter_name"]').attr('content')
        author_name = doc('meta[property="og:novel:author"]').attr('content')
        markeup = doc('meta[property="og:novel:category"]').attr('content')
        cover = doc('meta[property="og:image"]').attr('content')
        if not isinstance(cover, list):
            cover = [cover]

        info = {
            'name': book_name,
            'latest_chapter': latest_chapter_str,
            'desc': book_desc,
            'author_name': author_name,
            'markeup': markeup,
            'cover': cover
        }
        return info

    def parse_chapter(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode("gbk")

        doc = pq(data)
        dl_dd = doc('.zjlist>dd')
        chapter_list = []

        flag = False
        for dd in dl_dd:
            flag = dd.tag == 'dd'
            if flag:
                link = pq(pq(dd)('a')).attr('href')
                chapter_list.append(
                    {dd.text_content(): self.page_base_url + link})

        return chapter_list

    def get_content_info(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode("gbk")
        doc = pq(data)
        title = doc("#main > h1").text()
        content = doc("#content").text()
        return title, content

    def parse_chapter_content(self, data):
        _, content = self.get_content_info(data)
        return content

    def parse_chapter_singal(self, data):
        title, content = self.get_content_info(data)
        return {"title": title, "content": content}

    def parse_all_book(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode("gbk")
        doc = pq(data)
        novel_list = []
        novels = doc('#tlist > ul > li')
        for info in novels:
            title = pq(pq(info)('.zp>a')).text()
            url = pq(pq(info)('.zp>a')).attr('href')
            t = {'title': title, 'url': url, 'label': ""}
            if not url:
                continue
            novel_list.append(t)
        return novel_list