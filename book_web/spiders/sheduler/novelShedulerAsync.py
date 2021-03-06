import asyncio
import random
import time
from abc import ABCMeta, abstractmethod
import requests
import aiohttp
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
                logging.error(
                    'current normal requests error:<<<{}>>>: {}'.format(
                        e, url))
                proxies = get_proxy()
                retry -= 1
        return None

    async def async_do_request(self,
                               url,
                               content_type='text',
                               headers=None,
                               **kwargs):
        '''处理请求, url:请求地址'''

        retry = 5
        o_headers = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
        }
        headers = headers or o_headers
        conn = TCPConnector(limit=50)
        async with aiohttp.ClientSession(connector=conn) as session:
            while retry >= 0:
                try:
                    # if True:
                    proxies = get_proxy()
                    async with session.get(url,
                                           proxy=random.choice(proxies),
                                           verify_ssl=False,
                                           headers=headers,
                                           timeout=5) as res:

                        logging.info(
                            'current asyncio requests is {}:proxy:{}<<<{}>>> {}'
                            .format(str(retry), len(proxies), str(res.status),
                                    url))

                        if res.status > 400:
                            if res.status == 403:
                                raise aiohttp.ClientHttpProxyError
                            return None

                        if content_type == 'text':
                            return await res.text(**kwargs)
                        if content_type == 'read':
                            return await res.read(**kwargs)
                except (aiohttp.ClientHttpProxyError,
                        asyncio.exceptions.TimeoutError,
                        aiohttp.client_exceptions.ClientConnectorError):
                    proxies = get_proxy()
                    retry -= 1
                except Exception as e:
                    logging.error('异步请求异常：{}, 当前url: {}'.format(e, url))
                    return None

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

    async def save_image(self,
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
        tasks = []
        for img_url in img_list:
            task = asyncio.ensure_future(
                self.async_do_request(img_url, 'read', headers=headers))
            tasks.append(task)
        res_list = await asyncio.gather(*tasks)

        for idx, res in enumerate(res_list):
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

            lock.acquire()
            try:
                img.save()
            finally:
                lock.release()

            imgs.append(img)

        return imgs

    @abstractmethod
    async def handler(self):
        pass

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.handler())
        loop.run_until_complete(asyncio.sleep(0.1))
        # loop.close()


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

    async def handler(self):
        """处理书本信息"""

        res = self.do_request(self.url, self.headers)
        if not res or res.status_code != 200:
            return None, None
        self.book_info = self.parser(res)
        self.save_book_info_to_db(self.book_info)
        cover_list = await self.save_image(self.book_info['cover'],
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

    async def handler(self):
        """处理章节信息"""

        res = self.do_request(self.book.origin_addr, self.headers)
        if res:
            chapter_list = self.parser(res)
            self.save_chapter_list_to_db(chapter_list)


class ChapterContentClient(BaseClient):
    def __init__(self, chapter: Chapter = None, book: Book = None):
        self.chapter = chapter
        self.book = book
        origin_addr = book.origin_addr if book else chapter.origin_addr
        parser = parser_selector.get_parser(origin_addr)
        self.parser = parser.parse_chapter_content
        self.headers = parser.request_header if hasattr(
            parser, 'request_header') else None
        self.encoding = parser.encoding if hasattr(parser,
                                                   'encoding') else 'utf-8'

    @transaction.atomic
    async def handler_content(self, res, chapter: Chapter):
        content = self.parser(res)
        logging.info('处理<<{}>>{},正文信息:{}...'.format(chapter.book, chapter,
                                                    content[:15]))

        if chapter.book_type == BOOK_TYPE_DESC.Comic:
            imgs = []
            for key in content.keys():
                imgs.insert(int(key), content[key])
            img_objs = await self.save_image(imgs,
                                             IMAGE_TYPE_DESC.CHAPER_CONTENT,
                                             self.headers)
            # 如果能获取到所有img对象则保存
            if len(img_objs) and None not in img_objs:
                content = img_objs

        try:
            chapter.save_content(content)
            chapter.active = True
            chapter.save()
        except OSError:
            logging.error('处理<<{}>>单章节正文信息 失败 : {}'.format(
                chapter.book, chapter))
            chapter.active = False
            chapter.save()
            pass

    async def handler_single(self):
        res = self.do_request(self.chapter.origin_addr, self.headers)
        if res:
            content = self.parser(res)
            await self.handler_content(content, self.chapter)

    async def handler_all(self):
        all_chapter = Chapter.normal.filter(
            book_id=self.book.id, active=False,
            book_type=self.book.book_type).values('id', 'origin_addr')
        logging.info('<<{}>>: 所有章节正文 : 共{}条'.format(self.book,
                                                    len(all_chapter)))
        tasks = []
        for chapter in all_chapter:
            task = self.async_do_request(chapter['origin_addr'],
                                         'text',
                                         self.headers,
                                         encoding=self.encoding)

            tasks.append(task)
            if len(tasks) >= 30:
                res_list = await asyncio.gather(*tasks)
                await self.call_handler_content(all_chapter, res_list)
                tasks = []

        res_list = await asyncio.gather(*tasks)
        await self.call_handler_content(all_chapter, res_list)

    async def call_handler_content(self, all_chapter, res_list):
        for idx, res in enumerate(res_list):
            if not res:
                continue
            chapter = Chapter.normal.get(id=list(all_chapter)[idx]['id'])
            await self.handler_content(res, chapter)
        pass

    async def handler(self):
        if self.book:
            if not self.book.desc:
                # 更新书本介绍信息
                bic = BookInfoClient(self.book.origin_addr,
                                     self.book.book_type, self.book.on_shelf,
                                     self.book)
                await bic.handler()
            # 更新章节
            await self.handler_all()
        else:
            await self.handler_single()


class BookInsertClient(BaseClient):
    def __init__(self, url, book_type, insert_type='only_book', on_shelf=True):
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

    async def handler(self):
        bic = BookInfoClient(self.url, self.book_type, self.on_shelf)
        book, res = await bic.handler()
        if not book:
            return
        if self.type in ['with_chapter', 'with_content']:
            clc = ChapterListClient(book)
            if res:
                chapter_list = clc.parser(res)
                clc.save_chapter_list_to_db(chapter_list)
        if self.type == 'with_content':
            ccc = ChapterContentClient(book=book)
            await ccc.handler()


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

    async def handler(self):
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


class SlowAutoInsertBookClient(BaseClient):
    async def handler(self):
        logging.info("自动缓慢新增书籍开始执行！")
        for site in parser_selector.regular.keys():
            if not hasattr(parser_selector.get_parser(site),
                           'all_book_url_one_by_one'):
                continue

            parser_cls = parser_selector.get_parser(site)

            # for i in range(9, parser_cls.total_all_book):
            for i in range(284999, 285000):
                url = parser_cls.all_book_url_one_by_one.format(i)
                bic = BookInsertClient(url, parser_cls.book_type,
                                       'with_content')
                await bic.handler()


class FastAutoInsertBookClient(BaseClient):
    """多线程自动插入书本"""
    def __init__(self):
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
        bic = BookInsertClient(url, parser_cls.book_type, 'with_content')
        bic.run()
        time.sleep(1)
        lock.acquire()
        self.current_run_threading.remove(url)
        logging.info('当前还有线程 共 {} 条等待执行结束'.format(
            len(self.current_run_threading)))
        lock.release()

    def handler_threading(self, urls):
        logging.info("自动新增书籍开始执行，共有{}条".format(len(urls)))
        q = Queue(maxsize=100)
        st = time.time()
        all_len = len(urls) or 1
        while urls:
            url = urls.pop()
            print('\rurl 处理中 {} %'.format(
                str(100 * len(self.url_done) / all_len)),
                  end="")

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

    async def handler(self):
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

            for i in range(211, parser_cls.total_all_book):
                # for i in range(208, 210):
                url = parser_cls.all_book_url_one_by_one.format(i)
                if i in exist_urls:
                    continue
                urls.append(url)

                if len(urls) >= 20000:
                    self.handler_threading(urls)
                    urls = []

            self.handler_threading(urls)
        logging.info("自动快速新增书籍执行结束！共添加{}条数据".format(self.total_done))

    # async def handler(self):
    #     logging.info("自动新增书籍开始执行！")
    #     for site in parser_selector.regular.keys():
    #         if not hasattr(parser_selector.get_parser(site),
    #                        'all_book_url_one_by_one'):
    #             continue

    #         logging.info("自动新增书籍开始执行，{}".format(site))
    #         parser_cls = parser_selector.get_parser(site)

    #         for i in range(9, parser_cls.total_all_book):
    #             url = parser_cls.all_book_url_one_by_one.format(i)
    #             bic = BookInsertClient(url, parser_cls.book_type,
    #                                    'with_chapter')
    #             await bic.handler()


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

    async def do_all_book(self, parser_cls, start, end):
        tasks = []
        for i in range(start, end):
            url = parser_cls.all_book_url.format(i)

            task = self.async_do_request(url,
                                         'text',
                                         parser_cls.request_header,
                                         encoding=parser_cls.encoding)

            tasks.append(task)
        res_list = await asyncio.gather(*tasks)
        for res in res_list:
            if not res:
                continue
            book_info_list = parser_cls.parse_all_book(res)
            self.handler_all_book(book_info_list)

    async def handler(self):
        pass

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

                    await self.do_all_book(parser_cls, times * together_num,
                                           end_num)
                    times += 1
            else:
                await self.do_all_book(parser_cls, 1, parser_cls.total_page)


class BookUpdateClient(BaseClient):
    def __init__(self,
                 book_id=None,
                 chapter_id=None,
                 insert_type='only_chapters'):
        self.book_id = book_id
        self.chapter_id = chapter_id
        self.type = insert_type

    async def handler(self):
        if self.book_id:
            # 全书更新
            book = Book.normal.get(id=self.book_id)
            clc = ChapterListClient(book)
            await clc.handler()
            # 更新章节信息，不更新章节内容
            if self.type != 'only_chapters':
                ccc = ChapterContentClient(book=book)
                await ccc.handler()
        elif self.chapter_id:
            # 更新单章
            chapter = Chapter.normal.get(id=self.chapter_id)
            ccc = ChapterContentClient(chapter=chapter)
            await ccc.handler()
