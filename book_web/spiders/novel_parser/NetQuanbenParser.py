from book_web.spiders.novel_parser.BaseParser import BaseParser
from book_web.utils.spider_utils import validateFilename
from pyquery import PyQuery as pq
from book_web.utils.common_data import BOOK_TYPE_DESC


class NetQuanbenParser(BaseParser):
    book_type = BOOK_TYPE_DESC.Novel
    encoding = "utf-8"
    image_base_url = "https://www.quanben.net"
    page_base_url = "https://www.quanben.net"
    # 网站提供的全部小说列表
    all_book_url = "https://www.quanben.net/quanben/{}.html"
    total_page = 300
    # 网站实际全站小说
    all_book_url_one_by_one = "https://www.quanben.net/111/{}/"
    total_all_book = 293640
    total_all_book = 10

    filename_extension = "jpg"
    # request_header = {
    #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    #     "Accept-Encoding": "gzip, deflate, br",
    #     "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
    #     "Cache-Control": "no-cache",
    #     "Connection": "close",
    #     "Host": "www.quanben.net",
    #     "Pragma": "no-cache",
    #     "Referer": "https://www.quanben.net/290/290117/",
    #     "Upgrade-Insecure-Requests": "1",
    #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0",
    # }

    def parse_info(self, data):
        if data and hasattr(data, "content"):
            data = data.content.decode(self.encoding)

        doc = pq(data)
        book_name = doc(".btitle>h1").text()
        book_desc = doc("p.intro").text()
        latest_chapter_str = doc(
            "#container > div.bookinfo > p.stats > span.fl > a"
        ).text()
        author_name = doc("#container > div.bookinfo > div > em > a").text()
        markeup = doc("#wrapper > div.crumbs > div.fl > a:nth-child(3)").text()
        cover = ""
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
        dl_dd = doc(".chapterlist>dd")[9:]
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
        title = doc("#BookCon > h1").text()
        content = doc("#BookText").text()
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
        novels = doc("#content > div > div.details.list-type > ul > li")
        for info in novels:
            title = pq(pq(info)(".s2 > a")).text()
            author = pq(pq(info)(".s3")).text()
            url = pq(pq(info)(".s2 > a")).attr("href")
            label = pq(pq(info)(".s1")).text().replace("[", "").replace("]", "")
            if not url:
                continue
            t = {
                "title": validateFilename(title),
                "author": author,
                "url": self.page_base_url + url,
                "label": label,
            }
            novel_list.append(t)
        return novel_list
