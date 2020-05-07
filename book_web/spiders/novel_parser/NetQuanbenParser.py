from book_web.spiders.novel_parser.BaseParser import BaseParser
from pyquery import PyQuery as pq


class NetQuanbenParser(BaseParser):

    encoding = 'utf-8'
    image_base_url = 'https://www.quanben.net'
    page_base_url = 'https://www.quanben.net'
    all_book_url = 'https://www.quanben.net/quanben/{}.html'
    total_page = 300
    filename_extension = 'jpg'
    request_header = {
        'Accept':
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding':
        'gzip, deflate, br',
        'Accept-Language':
        'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Cache-Control':
        'no-cache',
        'Connection':
        'keep-alive',
        'Host':
        'www.quanben.net',
        'Pragma':
        'no-cache',
        'Referer':
        'https://www.quanben.net/290/290117/',
        'Upgrade-Insecure-Requests':
        '1',
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'
    }

    def parse_info(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)

        doc = pq(data)
        book_name = doc('.btitle>h1').text()
        book_desc = doc('p.intro').text()
        latest_chapter_str = doc(
            '#container > div.bookinfo > p.stats > span.fl > a').text()
        author_name = doc('#container > div.bookinfo > div > em > a').text()
        markeup = doc('#wrapper > div.crumbs > div.fl > a:nth-child(3)').text()
        cover = ""
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
            data = data.content.decode(self.encoding)

        doc = pq(data)
        dl_dd = doc('.chapterlist>dd')[10:]
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
            data = data.content.decode(self.encoding)
        doc = pq(data)
        title = doc("#BookCon > h1").text()
        content = doc("#BookText").text()
        return title, content

    def parse_chapter_content(self, data):
        _, content = self.get_content_info(data)
        return content

    def parse_chapter_singal(self, data):
        title, content = self.get_content_info(data)
        return {"title": title, "content": content}

    def parse_all_book(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)
        doc = pq(data)
        novel_list = []
        novels = doc('#content > div > div.details.list-type > ul > li')
        for info in novels:
            title = pq(pq(info)('.s2 > a')).text()
            author = pq(pq(info)('.s3')).text()
            url = pq(pq(info)('.s2 > a')).attr('href')
            label = pq(pq(info)('.s1')).text().replace('[',
                                                       '').replace(']', '')
            if not url:
                continue
            t = {
                'title': title,
                'author': author,
                'url': self.page_base_url + url,
                'label': label
            }
            novel_list.append(t)
        return novel_list