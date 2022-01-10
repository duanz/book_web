from book_web.spiders.novel_parser.BaseParser import BaseParser
from book_web.utils.spider_utils import validateFilename
from pyquery import PyQuery as pq
from book_web.utils.common_data import BOOK_TYPE_DESC


class TwQb5Parser(BaseParser):
    book_type = BOOK_TYPE_DESC.Novel
    encoding = "utf-8"
    image_base_url = "https://www.qb5.tw"
    page_base_url = "https://www.qb5.tw"
    all_book_url = "https://www.qb5.tw/quanben/{}"
    total_page = 1
    # total_page = 530
    filename_extension = "jpg"
    # request_header = {
    #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    #     "Accept-Encoding": "gzip, deflate, br",
    #     "Cache-Control": "no-cache",
    #     "Connection": "close",
    #     "Host": "https://www.qb5.tw",
    #     "Pragma": "no-cache",
    #     "Upgrade-Insecure-Requests": "1",
    #     "referer": "https://www.qb5.tw",
    #     "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36(KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36",
    # }

    def parse_info(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)

        doc = pq(data)
        book_name = doc('meta[property="og:title"]').attr("content")
        book_desc = doc('meta[property="og:description"]').attr("content")
        latest_chapter_str = doc('meta[property="og:novel:latest_chapter_name"]').attr(
            "content"
        )
        author_name = doc('meta[property="og:novel:author"]').attr("content")
        markeup = doc('meta[property="og:novel:category"]').attr("content")
        cover = doc('meta[property="og:image"]').attr("content")
        if not isinstance(cover, list):
            cover = [cover]

        info = {
            "name": validateFilename(book_name),
            "latest_chapter": validateFilename(latest_chapter_str),
            "desc": book_desc,
            "author_name": author_name,
            "markeup": markeup,
            "cover": cover,
        }
        return info

    def parse_chapter(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)

        doc = pq(data)
        dl_dd = doc(".zjlist>dd")
        chapter_list = []

        flag = False
        for dd in dl_dd:
            flag = dd.tag == "dd"
            if flag:
                link = pq(pq(dd)("a")).attr("href")
                chapter_list.append(
                    {validateFilename(dd.text_content()): self.page_base_url + link}
                )

        return chapter_list

    def get_content_info(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)
        doc = pq(data)
        title = doc("#main > h1").text()
        content = doc("#content").text()
        return validateFilename(title), content

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
        novels = doc("#tlist > ul > li")
        for info in novels:
            title = pq(pq(info)(".zp>a")).text()
            author = pq(pq(info)(".author")).text()
            url = pq(pq(info)(".zp>a")).attr("href")
            t = {
                "title": validateFilename(title),
                "url": url,
                "label": "",
                "author": author,
            }
            if not url:
                continue
            novel_list.append(t)
        return novel_list
