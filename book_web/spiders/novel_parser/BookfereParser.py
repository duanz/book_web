from book_web.spiders.novel_parser.BaseParser import BaseParser
from book_web.utils.spider_utils import validateFilename
from pyquery import PyQuery as pq
from book_web.utils.common_data import BOOK_TYPE_DESC


class BookfereParser(BaseParser):
    book_type = BOOK_TYPE_DESC.Novel
    encoding = "utf-8"

    request_header = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Connection": "close",
        "referer": "https://bookfere.com/post/category/news",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36",
    }

    def parse_info(self, data):
        pass

    def parse_chapter(self, data):
        print(data)
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)

        doc = pq(data)
        dl_dd = doc("#main article")
        # [{第一章：http://www.a.cc/1}，第二章, ...]
        chapter_list = []

        for u in dl_dd:
            u = u.find("header").find("h1").find("a")
            link = u.get("href")
            chapter_list.append({validateFilename(u.text_content()): link})
        return chapter_list

    def get_content_info(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)
        doc = pq(data)
        title = doc(".entry-title").text()
        eles = doc(".entry-content").children()[2:]
        content = ""
        for ele in eles:
            content += f"{ele.text_content()}。\r\n"
        return validateFilename(title), content

    def parse_chapter_content(self, data):
        _, content = self.get_content_info(data)
        return content

    def parse_chapter_singal(self, data):
        title, content = self.get_content_info(data)
        return {"title": title, "content": content}
