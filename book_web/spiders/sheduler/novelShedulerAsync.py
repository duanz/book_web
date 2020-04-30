import asyncio
import random
import time
from abc import ABCMeta, abstractmethod
import requests
import aiohttp
from django.core.cache import cache
from django.db import transaction
from book.models import IMAGE_TYPE_DESC, Author, Book, Chapter, Image, BOOK_TYPE_DESC
# for test
from book_web.utils.base_logger import logger as logging
from book_web.utils import photo as photo_lib
from book_web.utils import spider_parser_selector as parser_selector


class BaseClient(metaclass=ABCMeta):
    session = aiohttp.ClientSession()

    def proxy(self):
        ips = cache.get('proxy_ips')

        proxy = random.choice(list(ips.append('')))
        logging.info('current proxy is: {}'.format(proxy))
        return proxy

    def do_request(self, url):
        logging.info('current normal requests is: {}'.format(url))
        res = requests.get(url)
        return res

    async def async_do_request(self, url, content='text', **kwargs):
        '''处理请求, url:请求地址'''
        logging.info('current asyncio requests is: {}'.format(url))
        retry = 5
        while retry >= 0:
            try:
                async with self.session.get(url, proxy=self.proxy,
                                            timeout=20) as res:
                    logging.info('请求返回状态码 :{}'.format(res.status))
                    t = await getattr(res, content)(**kwargs)
                    return t
            except:
                retry -= 1

    async def async_do_request_read(self, url):
        '''处理请求, url:请求地址'''
        logging.info('current asyncio requests is: {}'.format(url))
        retry = 5
        while retry >= 0:
            try:
                async with self.session.get(url,
                                            proxy=self.proxy(),
                                            timeout=20) as res:
                    logging.info('请求返回状态码 :{}'.format(res.status))
                    t = await res.read()
                    return t
            except:
                retry -= 1

    async def save_image(self, images: list) -> list:
        logging.info('保存图片到数据库')
        imgs = []
        for idx, img_url in enumerate(images):

            img, flag = Image.normal.get_or_create(
                origin_addr=img_url[-200:], img_type=IMAGE_TYPE_DESC.COVER)

            if flag:
                print(img_url)
                res_data = self.do_request(img_url).content
                # res_data = await self.async_do_request_read(img_url)
                if not res_data:
                    img.delete()
                    continue
                photo_info = photo_lib.save_binary_photo(res_data)

                img.key = photo_info['id']
                img.name = photo_info['name']
                img.save()
            imgs.append(img)
        return imgs

    @abstractmethod
    async def handler(self):
        pass

    @transaction.atomic
    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.handler())
        loop.run_until_complete(self.session.close())
        loop.close()


class BookInfoClient(BaseClient):
    def __init__(self, url, book_type):
        self.url = url
        self.book_type = book_type

        parser = parser_selector.get_parser(url)
        self.parser = parser.parse_info
        self.encoding = parser.encoding if hasattr(parser,
                                                   'encoding') else 'utf-8'

    def save_or_get_author_db(self, info):
        author, flag = Author.normal.get_or_create(name=info['author_name'])
        return author

    def save_book_info_to_db(self, info):
        '''保存书本信息到数据库'''
        logging.info('保存书本信息到数据库')

        author = self.save_or_get_author_db(info)
        book, flag = Book.normal.get_or_create(title=info['name'],
                                               author=author,
                                               book_type=self.book_type)
        book.book_type = self.book_type
        book.title = info.get('name')
        book.author = author
        book.desc = info.get('desc')
        book.markeup = info.get('markeup')
        book.origin_addr = self.url
        book.save()
        self.book = book
        return book

    async def handler(self):
        """处理书本信息"""
        logging.info('current handler is : {}'.format(self.__class__))

        res = self.do_request(self.url)
        self.book_info = self.parser(res)
        self.save_book_info_to_db(self.book_info)
        cover_list = await self.save_image(self.book_info['cover'])
        self.book.cover.add(*cover_list)
        self.book.save()


class ChapterListClient(BaseClient):
    def __init__(self, book: Book):
        self.book = book
        self.book_type = book.book_type

        parser = parser_selector.get_parser(book.origin_addr)
        self.parser = parser.parse_chapter
        self.encoding = parser.encoding if hasattr(parser,
                                                   'encoding') else 'utf-8'

    async def save_chapter_list_to_db(self, chapter_list):
        '''保存章节信息到数据库'''
        for index, chapter_dict in enumerate(chapter_list, 0):
            chapter_title = list(chapter_dict.keys())[0]
            chapter_link = list(chapter_dict.values())[0]

            chapter_obj, flag = Chapter.normal.get_or_create(
                book=self.book, book_type=self.book_type, title=chapter_title)
            chapter_obj.book = self.book
            chapter_obj.title = chapter_title
            chapter_obj.order = index
            chapter_obj.origin_addr = chapter_link
            chapter_obj.save()

    @transaction.atomic
    async def handler(self):
        """处理章节信息"""

        res = self.do_request(self.book.origin_addr)
        if res:
            chapter_list = self.parser(res)
            await self.save_chapter_list_to_db(chapter_list)


class ChapterContentClient(BaseClient):
    def __init__(self, chapter: Chapter = None, book: Book = None):
        self.chapter = chapter
        self.book = book
        origin_addr = book.origin_addr if book else chapter.origin_addr
        parser = parser_selector.get_parser(origin_addr)
        self.parser = parser.parse_chapter_content
        self.encoding = parser.encoding if hasattr(parser,
                                                   'encoding') else 'utf-8'

    @transaction.atomic
    async def handler_single(self):
        """处理单章节正文信息"""
        res = self.do_request(self.chapter.origin_addr)
        if res:
            content = self.parser(res)
            self.chapter.save_content(content)

    @transaction.atomic
    async def handler_all(self):
        """处理所有章节正文信息"""
        all_chapter = Chapter.normal.filter(book=self.book,
                                            active=False,
                                            book_type=self.book.book_type)
        for chapter in all_chapter:
            res = await self.async_do_request(chapter.origin_addr,
                                              'text',
                                              encoding=self.encoding)
            if res:
                content = self.parser(res)
                chapter.save_content(content)

    @transaction.atomic
    async def handler(self):
        """处理章节正文信息"""
        if self.book:
            await self.handler_all()
        else:
            await self.handler_single()


class BookInsertClient(BaseClient):
    def __init__(self, url, book_type):
        self.url = url
        self.book_type = book_type

    async def handler(self):
        bic = BookInfoClient(self.url, self.book_type)
        await bic.handler()
        book = Book.normal.get(origin_addr=self.url)
        clc = ChapterListClient(book)
        await clc.handler()
        ccc = ChapterContentClient(book=book)
        await ccc.handler()


class BookUpdateClient(BaseClient):
    def __init__(self, book_id=None, chapter_id=None):
        self.book_id = book_id
        self.chapter_id = chapter_id

    async def handler(self):
        if self.book_id:
            # 全书更新
            book = Book.normal.get(id=self.book_id)
            clc = ChapterListClient(book)
            await clc.handler()
            ccc = ChapterContentClient(book=book)
            await ccc.handler()
        elif self.chapter_id:
            # 更新单章
            chapter = Chapter.normal.get(id=self.chapter_id)
            ccc = ChapterContentClient(chapter=chapter)
            await ccc.handler()