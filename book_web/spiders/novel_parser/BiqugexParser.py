from book_web.spiders.novel_parser.BaseParser import BaseParser
from book_web.utils.spider_utils import validateFilename
from pyquery import PyQuery as pq
from book_web.utils.common_data import BOOK_TYPE_DESC


class BiqugexParser(BaseParser):
    book_type = BOOK_TYPE_DESC.Novel
    encoding = "gbk"
    image_base_url = "http://www.biquge.tv"
    page_base_url = "http://www.biquge.tv"
    all_book_url = "http://www.biquge.tv/xiaoshuodaquan/"
    total_page = 51
    # 网站实际全站小说
    all_book_url_one_by_one = "http://www.biquge.tv/26_{}/"
    # total_all_book = 41933
    total_all_book = 41
    filename_extension = "jpg"
    # request_header = {
    #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    #     "Accept-Encoding": "gzip, deflate, br",
    #     "Cache-Control": "no-cache",
    #     "Connection": "close",
    #     "Host": "www.biquge.tv",
    #     "Pragma": "no-cache",
    #     "Upgrade-Insecure-Requests": "1",
    #     "referer": "www.biquge.tv",
    #     "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36",
    # }

    def parse_info(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)

        doc = pq(data)
        book_name = doc('meta[property="og:title"]').attr("content")
        book_desc = (
            doc('meta[property="og:description"]').attr("content").replace("\xa0", "")
        )
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
        dl_dd = doc("#list dl").children()[1:]
        # [{第一章：http://www.a.cc/1}，第二章, ...]
        chapter_list = []

        flag = False
        for u in dl_dd:
            if flag:
                link = u.find("a").get("href")
                chapter_list.append(
                    {validateFilename(u.text_content()): self.page_base_url + link}
                )
            else:
                flag = u.tag == "dt"

        return chapter_list

    def get_content_info(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)
        doc = pq(data)
        title = doc(".content h1").text()
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
        novels = doc(".novellist")
        for block in novels:
            b = pq(block).html()
            label = pq(b)("h2").text()
            book_list = pq(pq(b)("ul"))("li")
            for info in book_list:
                title = pq(info).text()
                url = pq(pq(info)("a")).attr("href")
                t = {"title": validateFilename(title), "url": url, "label": label}
                if not url:
                    continue
                novel_list.append(t)
        return novel_list
