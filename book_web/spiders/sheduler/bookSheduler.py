import random
import time
from abc import ABCMeta, abstractmethod
import requests
import threading
from queue import Queue
from aiohttp import TCPConnector
from django.core.cache import cache
from django.db import transaction
from book.models import Author, Book, Chapter, Image
from book_web.utils.common_data import IMAGE_TYPE_DESC, BOOK_TYPE_DESC
# for test
from book_web.utils.base_logger import logger as logging
from book_web.utils import photo as photo_lib
from book_web.utils import spider_parser_selector as parser_selector

lock = threading.RLock()


def get_proxy():
    ips = cache.get('proxy_ips')
    if ips is None:
        return None

    ips.append(None)
    # ip = random.choice(ips)
    # return ip
    return ips


class BaseClient(metaclass=ABCMeta):
    def do_request(self, url, headers=None):
        retry = 5
        o_headers = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
        }
        headers = headers or o_headers
        while retry >= 0:
            try:
                proxies = get_proxy()
                res = requests.get(url,
                                   headers=headers,
                                   proxies={'http': random.choice(proxies)},
                                   verify=False,
                                   timeout=5)
                logging.info(
                    'normal requests:<<<{}>>> PROXY:{}, URL {}'.format(
                        res.status_code, len(proxies), url))
                return res
            except Exception as e:
                if retry == 0:
                    logging.error(
                        'current normal requests error:<<<{}>>>: {}'.format(
                            e, url))
                proxies = get_proxy()
                retry -= 1
        return None

    def check_image(self, urls: list):
        exist_imgs = Image.normal.filter(origin_addr__in=urls).exclude(
            key='', name='').values('origin_addr')
        exist_url = exist_imgs.values()
        need = []
        for url in urls:
            if url and (url not in exist_url):
                need.append(url)

        return need

    def save_image(self,
                   images: list,
                   image_type=IMAGE_TYPE_DESC.COVER,
                   headers=None) -> list:
        """
        images：需要保存的图片连接列表；
        检查images中新image，即未保存过的图片连接；
        保存所有新image,如果失败，任然保存成功的;
        返回images对应的image对象列表，失败部分则以None代替
        """
        img_list = self.check_image(images)
        logging.info('需要保存的 {} 图片共有 {} 条'.format(image_type, len(img_list)))
        imgs = []
        for idx, img_url in enumerate(img_list, 0):
            res = self.do_request(img_url, headers=headers).content

            if not res:
                imgs.append(None)
                continue

            lock.acquire()
            try:
                img, flag = Image.normal.get_or_create(
                    origin_addr=img_list[idx], )
            finally:
                lock.release()

            if not img.key or flag:
                photo_info = photo_lib.save_binary_photo(res)
                key = photo_info['id']
                name = photo_info['name']

                img.img_type = image_type
                img.active = True
                img.key = key
                img.name = name
                lock.acquire()
                img.save()

            imgs.append(img)

        return imgs

    @abstractmethod
    def handler(self):
        pass

    def run(self):
        return self.handler()


class BookInfoClient(BaseClient):
    def __init__(self, url, book_type, on_shelf=True, book=None):
        self.url = url
        self.book_type = book_type
        self.on_shelf = on_shelf
        self.book = book

        parser = parser_selector.get_parser(url)
        self.parser = parser.parse_info
        self.headers = parser.request_header if hasattr(
            parser, 'request_header') else None
        self.encoding = parser.encoding if hasattr(parser,
                                                   'encoding') else 'utf-8'

    def save_or_get_author_db(self, info):
        lock.acquire()
        try:
            author, flag = Author.normal.get_or_create(
                name=info['author_name'])
        except Author.MultipleObjectsReturned:
            author = Author.normal.filter(name=info['author_name']).first()
        finally:
            lock.release()

        return author

    def save_book_info_to_db(self, info):
        '''保存书本信息到数据库'''
        logging.info('保存<<{}>>信息到数据库'.format(info['name']))

        author = self.save_or_get_author_db(info)

        book = self.book
        if not self.book:
            lock.acquire()
            try:
                books = Book.normal.filter(title=info['name'],
                                           author=author,
                                           book_type=self.book_type)
                if books.count() > 0:
                    book = books[0]
                    for book in books[1:]:
                        book.delete()
                else:
                    book = Book()

                if not book.desc:
                    book.book_type = self.book_type
                    book.title = info.get('name')
                    book.author = author
                    book.desc = info.get('desc')
                    book.markeup = info.get('markeup')
                    book.origin_addr = self.url
                    book.on_shelf = self.on_shelf
                    book.save()
            finally:
                lock.release()
        self.book = book
        return book

    def handler(self):
        """处理书本信息"""

        res = self.do_request(self.url, self.headers)
        if not res or res.status_code != 200:
            return None, None
        self.book_info = self.parser(res)
        self.save_book_info_to_db(self.book_info)
        cover_list = self.save_image(self.book_info['cover'],
                                     headers=self.headers)
        logging.info(cover_list)
        if cover_list and all(cover_list):
            self.book.cover.add(*cover_list)
        lock.acquire()
        try:
            self.book.save()
        finally:
            lock.release()
        return self.book, res


class ChapterListClient(BaseClient):
    def __init__(self, book: Book):
        self.book = book
        self.book_type = book.book_type

        parser = parser_selector.get_parser(book.origin_addr)
        self.parser = parser.parse_chapter
        self.headers = parser.request_header if hasattr(
            parser, 'request_header') else None
        self.encoding = parser.encoding if hasattr(parser,
                                                   'encoding') else 'utf-8'

    def check_chapters(self, chapter_dick_list):
        titles = []
        chapter_list = []
        for chapter_dict in chapter_dick_list:
            title = list(chapter_dict.keys())[0]
            link = list(chapter_dict.values())[0]
            titles.append(title)
            chapter_list.append(link)

        exits_chapter = Chapter.normal.filter(
            book_id=self.book.id, title__in=titles).values_list('title')
        exits_title = [i[0] for i in exits_chapter]
        new_urls = []
        for idx, i in enumerate(titles, 0):
            if i and (i not in exits_title):
                new_urls.append(chapter_list[idx])
        return new_urls

    def bulk_create_chapter(self, chapters):
        lock.acquire()
        try:
            Chapter.normal.bulk_create(chapters)
        finally:
            lock.release()

    def save_chapter_list_to_db(self, chapter_dick_list):
        '''保存章节信息到数据库'''
        new_urls = self.check_chapters(chapter_dick_list)
        logging.info("即将保存《{}》的{}条新章节到数据库".format(self.book, len(new_urls)))
        need_create = []
        for index, chapter_dict in enumerate(chapter_dick_list, 0):
            chapter_title = list(chapter_dict.keys())[0]
            chapter_link = list(chapter_dict.values())[0]

            if chapter_link in new_urls:
                chapter = Chapter(title=chapter_title,
                                  origin_addr=chapter_link,
                                  order=index,
                                  book_type=self.book.book_type,
                                  book_id=self.book.id,
                                  number=index)
                need_create.append(chapter)

            if len(need_create) >= 200:
                self.bulk_create_chapter(need_create)
                need_create = []

        self.bulk_create_chapter(need_create)

    def handler(self):
        """处理章节信息"""

        res = self.do_request(self.book.origin_addr, self.headers)
        if res:
            chapter_list = self.parser(res)
            self.save_chapter_list_to_db(chapter_list)


class ChapterContentClient(BaseClient):
    def __init__(self, chapter: Chapter = None, book: Book = None, fast=False):
        self.chapter = chapter
        self.book = book
        self.fast = fast
        self.wait_done = 0
        origin_addr = book.origin_addr if book else chapter.origin_addr
        parser = parser_selector.get_parser(origin_addr)
        self.parser = parser.parse_chapter_content
        self.headers = parser.request_header if hasattr(
            parser, 'request_header') else None
        self.encoding = parser.encoding if hasattr(parser,
                                                   'encoding') else 'utf-8'

    @transaction.atomic
    def handler_content(self, content, chapter: Chapter):
        logging.info('处理--{}--<<{}>>{},正文信息:{}...'.format(
            self.wait_done, chapter.book, chapter, content[:10]))
        if chapter.book_type == BOOK_TYPE_DESC.Comic:
            imgs = []
            for key in content.keys():
                imgs.insert(int(key), content[key])
            img_objs = self.save_image(imgs, IMAGE_TYPE_DESC.CHAPER_CONTENT,
                                       self.headers)
            # 如果能获取到所有img对象则保存
            if len(img_objs) and None not in img_objs:
                content = img_objs

        try:
            if not content:
                raise OSError
            chapter.save_content(content)
            chapter.active = True
            chapter.save()
        except OSError:
            logging.error('处理<<{}>>单章节正文信息 失败 : {}'.format(
                chapter.book, chapter))
            chapter.active = False
            chapter.save()
            pass

    def handler_single(self, chapter=None):
        lock.acquire()
        self.wait_done += 1
        lock.release()
        res = self.do_request(chapter.origin_addr or self.chapter.origin_addr,
                              self.headers)
        if res:
            content = self.parser(res)
            self.handler_content(content, chapter or self.chapter)
        lock.acquire()
        self.wait_done -= 1
        lock.release()

    def thread_handler_all(self):
        all_chapter = Chapter.normal.filter(book_id=self.book.id,
                                            active=False,
                                            book_type=self.book.book_type)
        chapter_list = list(all_chapter)
        logging.info('<<{}>>: 需要更新章节正文 : 共{}条'.format(self.book,
                                                      len(all_chapter)))
        q = Queue(maxsize=20)
        st = time.time()
        self.wait_done = len(chapter_list) or 0
        while chapter_list:
            chapter = chapter_list.pop()

            t = threading.Thread(target=self.handler_single, args=(chapter, ))
            q.put(t)
            if (q.full() == True) or (len(chapter_list)) == 0:
                thread_list = []
                while q.empty() == False:
                    t = q.get()
                    t.setDaemon(True)
                    thread_list.append(t)
                    t.start()
                for t in thread_list:
                    t.join(5)
        logging.info('当前还有处理 {} 的线程 共 {} 条等待执行结束'.format(
            self.book, self.wait_done))

    def handler_all(self):
        all_chapter = Chapter.normal.filter(book_id=self.book.id,
                                            active=False,
                                            book_type=self.book.book_type)
        logging.info('<<{}>>: 所有章节正文 : 共{}条'.format(self.book,
                                                    len(all_chapter)))
        tasks = []
        for chapter in all_chapter:
            res = self.do_request(chapter.origin_addr, self.headers)

            if res:
                content = self.parser(res)
                self.handler_content(content, chapter)

    def handler(self):
        if self.book:
            if not self.book.desc:
                # 更新书本介绍信息
                bic = BookInfoClient(self.book.origin_addr,
                                     self.book.book_type, self.book.on_shelf,
                                     self.book)
                bic.run()
            # 更新章节
            if self.fast:
                # 使用多线程
                self.thread_handler_all()
            else:
                self.handler_all()
        else:
            self.handler_single()


class BookInsertClient(BaseClient):
    def __init__(self,
                 url,
                 book_type,
                 insert_type='only_book',
                 on_shelf=True,
                 fast=False):
        """
        insert_type:
            only_book: 只添加书本信息
            with_chapter：添加书本信息及其章节信息
            with_content：添加书本信息，章节信息，和章节内容
        """
        self.url = url
        self.book_type = book_type
        self.type = insert_type
        self.on_shelf = on_shelf
        self.fast = fast

    def handler(self):
        bic = BookInfoClient(self.url, self.book_type, self.on_shelf)
        book, res = bic.handler()
        if not book:
            return
        if self.type in ['with_chapter', 'with_content']:
            clc = ChapterListClient(book)
            if res:
                chapter_list = clc.parser(res)
                clc.save_chapter_list_to_db(chapter_list)
        if self.type == 'with_content':
            ccc = ChapterContentClient(book=book, fast=self.fast)
            ccc.handler()


class OldBookAutoInsertClient(BaseClient):
    """自动插入书本信息，不包含章节内容"""
    def __init__(self, url):
        self.url = url
        parser = parser_selector.get_parser(url)
        self.parser = parser.parse_all_book
        self.headers = parser.request_header if hasattr(
            parser, 'request_header') else None
        self.encoding = parser.encoding if hasattr(parser,
                                                   'encoding') else 'utf-8'

    def handler(self):
        res = self.do_request(self.url, self.headers)
        book_info_list = self.parser(res)
        count = 0
        author, _ = Author.normal.get_or_create(name='未知')
        exist = Book.normal.filter(
            origin_addr__in=[info['url']
                             for info in book_info_list]).values('origin_addr')
        exist_url = [i['origin_addr'] for i in exist]
        need_url = [i for i in book_info_list if i['url'] not in exist_url]
        books = []
        for idx, info in enumerate(need_url, 1):
            logging.info('新自动插入书{}/{}条： {}  {}'.format(idx, len(need_url),
                                                       info['title'],
                                                       info['url']))
            book = Book(on_shelf=False,
                        author=author,
                        book_type=BOOK_TYPE_DESC.Novel,
                        title=info['title'][:60],
                        markup=info['label'][:100],
                        origin_addr=info['url'][:200])
            books.append(book)

            if len(books) >= 500:
                Book.normal.bulk_create(books)
                books = []
        Book.normal.bulk_create(books)


class AutoInsertBookClient(BaseClient):
    """多线程自动插入书本"""
    def __init__(self, insert_type='with_chapter'):
        """
        insert_type
            with_chapter: 只保存书本及其章节信息
            with_content: 保存书本，章节和正文信息
        """
        self.url_done = []
        self.total_done = 0
        self.current_run_threading = []

    def book_insert(self, url):
        lock.acquire()
        if url and (url not in self.url_done):
            self.url_done.append(url)
            self.total_done += 1
        else:
            return
        self.current_run_threading.append(url)
        lock.release()
        parser_cls = parser_selector.get_parser(url)
        # bic = BookInsertClient(url, parser_cls.book_type, 'with_chapter')
        bic = BookInsertClient(url, parser_cls.book_type, 'with_content', True,
                               True)
        bic.run()
        lock.acquire()
        self.current_run_threading.remove(url)
        logging.info('当前还有线程 共 {} 条等待执行结束'.format(
            len(self.current_run_threading)))
        lock.release()

    def handler_threading(self, urls):
        logging.info("自动新增书籍开始执行，共有{}条".format(len(urls)))
        q = Queue(maxsize=20)
        st = time.time()
        all_len = len(urls) or 1
        while urls:
            url = urls.pop()

            t = threading.Thread(target=self.book_insert, args=(url, ))
            q.put(t)
            if (q.full() == True) or (len(urls)) == 0:
                thread_list = []
                while q.empty() == False:
                    t = q.get()
                    t.setDaemon(True)
                    thread_list.append(t)
                    t.start()
                for t in thread_list:
                    t.join(5)
        logging.info('当前还有处理 {} 的线程 共 {} 条等待执行结束'.format(
            self.current_run_threading, len(self.current_run_threading)))

    def handler(self):
        logging.info("自动快速新增书籍开始执行！")

        for site in parser_selector.regular.keys():
            if not hasattr(parser_selector.get_parser(site),
                           'all_book_url_one_by_one'):
                continue

            parser_cls = parser_selector.get_parser(site)

            self.url_done = []
            urls = []
            exist = Book.normal.all().values_list('origin_addr')
            exist_urls = [i[0] for i in exist]

            for i in range(1, parser_cls.total_all_book):
                # for i in range(214, 250):
                url = parser_cls.all_book_url_one_by_one.format(i)
                if i in exist_urls:
                    continue
                urls.append(url)

                if len(urls) >= 20000:
                    self.handler_threading(urls)
                    urls = []

            self.handler_threading(urls)
        logging.info("自动快速新增书籍执行结束！共添加{}条数据".format(self.total_done))


class BookAutoInsertClient(BaseClient):
    """自动插入书本信息，不包含章节内容"""
    def handler_all_book(self, book_info_list):
        logging.info("自动插入书本信息,即将处理{}条数据".format(len(book_info_list)))
        count = 0
        author, _ = Author.normal.get_or_create(name='未知')
        exist = Book.normal.filter(
            origin_addr__in=[info['url']
                             for info in book_info_list]).values('origin_addr')
        exist_url = [i['origin_addr'] for i in exist]
        need_url = [i for i in book_info_list if i['url'] not in exist_url]
        books = []
        for idx, info in enumerate(need_url, 1):
            logging.info('新自动插入书{}/{}条： {}  {}'.format(idx, len(need_url),
                                                       info['title'],
                                                       info['url']))
            if info.get('author', None):
                retry = 5
                while retry > 0:
                    try:
                        author, _ = Author.normal.get_or_create(
                            name=info['author'])
                    except:
                        retry -= 1
            book = Book(on_shelf=False,
                        author=author,
                        book_type=BOOK_TYPE_DESC.Novel,
                        title=info['title'][:60],
                        markup=info['label'][:100],
                        origin_addr=info['url'][:200])
            books.append(book)

            if len(books) >= 500:
                Book.normal.bulk_create(books)
                books = []
        Book.normal.bulk_create(books)

    def do_all_book(self, parser_cls, start, end):
        for i in range(start, end):
            url = parser_cls.all_book_url.format(i)

            res = self.do_request(url, parser_cls.request_header)
            if not res:
                continue
            book_info_list = parser_cls.parse_all_book(res)
            self.handler_all_book(book_info_list)

    def handler(self):
        logging.info("自动新增书籍开始执行！")
        for site in parser_selector.regular.keys():
            if not hasattr(parser_selector.get_parser(site), 'parse_all_book'):
                continue

            logging.info("自动新增书籍开始执行，{}".format(site))
            parser_cls = parser_selector.get_parser(site)

            # 同时发送请求数
            together_num = 50

            if parser_cls.total_page > together_num:
                tasks = []
                num = parser_cls.total_page // together_num
                times = 0
                while times * together_num < parser_cls.total_page:
                    end_num = parser_cls.total_page if (
                        parser_cls.total_page - times * together_num
                    ) < together_num else (times + 1) * together_num

                    self.do_all_book(parser_cls, times * together_num, end_num)
                    times += 1
            else:
                self.do_all_book(parser_cls, 1, parser_cls.total_page)


class BookUpdateClient(BaseClient):
    def __init__(self,
                 book_id=None,
                 chapter_id=None,
                 insert_type='only_chapters',
                 fast=False):
        self.book_id = book_id
        self.chapter_id = chapter_id
        self.type = insert_type
        self.fast = fast

    def handler(self):
        if self.book_id:
            # 全书更新
            book = Book.normal.get(id=self.book_id)
            clc = ChapterListClient(book)
            clc.handler()
            # 更新章节信息，不更新章节内容
            if self.type != 'only_chapters':
                ccc = ChapterContentClient(book=book, fast=self.fast)
                ccc.handler()
        elif self.chapter_id:
            # 更新单章
            chapter = Chapter.normal.get(id=self.chapter_id)
            ccc = ChapterContentClient(chapter=chapter)
            ccc.handler()
