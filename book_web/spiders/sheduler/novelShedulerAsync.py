import asyncio
import random
import time
from abc import ABCMeta, abstractmethod
import requests
import aiohttp
from aiohttp import TCPConnector
from django.core.cache import cache
from django.db import transaction
from book.models import IMAGE_TYPE_DESC, Author, Book, Chapter, Image, BOOK_TYPE_DESC
# for test
from book_web.utils.base_logger import logger as logging
from book_web.utils import photo as photo_lib
from book_web.utils import spider_parser_selector as parser_selector


class BaseClient(metaclass=ABCMeta):
    def proxy(self):
        ips = cache.get('proxy_ips')
        if ips is None:
            return None

        ips.append(None)
        ip = random.choice(ips)
        return ip

    def do_request(self, url):
        res = requests.get(url)
        logging.info('current normal requests is:<<<{}>>> {}'.format(
            res.status_code, url))
        return res

    async def async_do_request(self,
                               url,
                               content_type='text',
                               headers=None,
                               **kwargs):
        '''处理请求, url:请求地址'''

        retry = 5
        proxy = self.proxy()
        o_headers = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
        }
        headers = headers or o_headers
        conn = TCPConnector(limit=10)
        async with aiohttp.ClientSession(connector=conn) as session:
            while retry >= 0:
                try:
                    # if True:
                    async with session.get(url,
                                           proxy=proxy,
                                           verify_ssl=False,
                                           headers=headers,
                                           timeout=5) as res:

                        logging.info(
                            'current asyncio requests is {}:proxy:{}<<<{}>>> {}'
                            .format(str(retry), proxy, str(res.status), url))

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
                    proxy = self.proxy()
                    retry -= 1
                except Exception as e:
                    # logging.error('异步请求异常：{}, 当前url: {}'.format(e, url))
                    logging.error('异步请求异常：{}'.format(e))
                    return None

            return None

    def check_image(self, urls: list):
        exist_imgs = Image.normal.filter(origin_addr__in=urls).exclude(
            key='', name='').values('origin_addr')
        exist_url = exist_imgs.values()
        need = []
        for url in urls:
            if url not in exist_url:
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
            img, flag = Image.normal.get_or_create(origin_addr=img_list[idx], )
            if not img.key or flag:
                photo_info = photo_lib.save_binary_photo(res)
                key = photo_info['id']
                name = photo_info['name']

                img.img_type = image_type
                img.active = True
                img.key = key
                img.name = name
                img.save()
            imgs.append(img)

        return imgs

    @abstractmethod
    async def handler(self):
        pass

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.handler())
        loop.close()


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
        author, flag = Author.normal.get_or_create(name=info['author_name'])
        return author

    def save_book_info_to_db(self, info):
        '''保存书本信息到数据库'''
        logging.info('保存<<{}>>信息到数据库'.format(info['name']))

        author = self.save_or_get_author_db(info)

        book = self.book
        if not self.book:
            book, flag = Book.normal.get_or_create(title=info['name'],
                                                   author=author,
                                                   book_type=self.book_type)
        book.book_type = self.book_type
        book.title = info.get('name')
        book.author = author
        book.desc = info.get('desc')
        book.markeup = info.get('markeup')
        book.origin_addr = self.url
        book.on_shelf = self.on_shelf
        book.save()
        self.book = book
        return book

    async def handler(self):
        """处理书本信息"""
        logging.info('current handler is : {}'.format(self.__class__))

        res = self.do_request(self.url)
        self.book_info = self.parser(res)
        self.save_book_info_to_db(self.book_info)
        cover_list = await self.save_image(self.book_info['cover'],
                                           headers=self.headers)
        logging.info(cover_list)
        if cover_list and all(cover_list):
            self.book.cover.add(*cover_list)
        self.book.save()


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
            chapter_obj.number = index
            chapter_obj.origin_addr = chapter_link
            chapter_obj.save()

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
        self.headers = parser.request_header if hasattr(
            parser, 'request_header') else None
        self.encoding = parser.encoding if hasattr(parser,
                                                   'encoding') else 'utf-8'

    @transaction.atomic
    async def handler_content(self, res, chapter: Chapter):
        logging.info('处理<<{}>>单章节正文信息: {}'.format(chapter.book, chapter))
        content = self.parser(res)
        if chapter.book_type == BOOK_TYPE_DESC.Comic:
            imgs = []
            for key in content.keys():
                imgs.insert(int(key), content[key])
            img_objs = await self.save_image(imgs,
                                             IMAGE_TYPE_DESC.CHAPER_CONTENT,
                                             self.headers)
            # 如果能获取到所有img对象则保存
            if len(img_objs) and None not in img_objs:
                # chapter.save_content(img_objs)
                content = img_objs
        # elif chapter.book_type == BOOK_TYPE_DESC.Novel:
        try:
            chapter.save_content(content)
        except OSError:
            logging.info('处理<<{}>>单章节正文信息: {}, 失败'.format(
                chapter.book, chapter))
            chapter.active = False
            chapter.save()
            pass

    async def handler_single(self):
        res = self.do_request(self.chapter.origin_addr)
        if res:
            content = self.parser(res)
            await self.handler_content(content, self.chapter)

    async def handler_all(self):
        all_chapter = Chapter.normal.filter(
            book=self.book, active=False,
            book_type=self.book.book_type).values('id', 'origin_addr')
        logging.info('处理<<{}>>所有章节正文信息: 共{}条'.format(self.book,
                                                     len(all_chapter)))
        tasks = []
        for chapter in all_chapter:
            task = self.async_do_request(chapter['origin_addr'],
                                         'text',
                                         self.headers,
                                         encoding=self.encoding)

            tasks.append(task)
        res_list = await asyncio.gather(*tasks)
        for idx, res in enumerate(res_list):
            if not res:
                continue
            chapter = Chapter.normal.get(id=list(all_chapter)[idx]['id'])
            await self.handler_content(res, chapter)

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
            with_chapters：添加书本信息及其章节信息
            with_content：添加书本信息，章节信息，和章节内容
        """
        self.url = url
        self.book_type = book_type
        self.type = insert_type
        self.on_shelf = on_shelf

    async def handler(self):
        bic = BookInfoClient(self.url, self.book_type, self.on_shelf)
        await bic.handler()
        if self.type == 'with_chapters':
            book = Book.normal.get(origin_addr=self.url)
            clc = ChapterListClient(book)
            await clc.handler()
        if self.type == 'with_content':

            book = Book.normal.get(origin_addr=self.url)
            clc = ChapterListClient(book)
            await clc.handler()

            ccc = ChapterContentClient(book=book)
            await ccc.handler()


class BookAutoInsertClient(BaseClient):
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
        res = self.do_request(self.url)
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


# import asyncio, logging, aiohttp

# class A:
#     async def async_do_request(self, url, content_type='text', **kwargs):
#         '''处理请求, url:请求地址'''
#         logging.info('current asyncio requests is: {}'.format(url))
#         retry = 5
#         while retry >= 0:
#             async with aiohttp.ClientSession() as session:
#                 try:
#                     async with session.get(url, timeout=20) as res:
#                         logging.info('请求返回状态码 :{}'.format(res.status))

#                         if content_type == 'text':
#                             return await res.text(**kwargs)
#                         if content_type == 'read':
#                             return await res.read(**kwargs)
#                 except:
#                     retry -= 1

#     async def handler(self):
#         tasks = []
#         for i in range(10):
#             url = 'https://www.so.com/s?ie=utf-8&fr=none&src=360sou_newhome&nlpv=3.7.3st&q={}'.format(
#                 i)
#             task = asyncio.ensure_future(self.async_do_request(url))

#             tasks.append(task)
#         res_list = await asyncio.gather(*tasks)
#         for idx, res in enumerate(res_list):
#             with open('{}.html'.format(idx), 'w', encoding='utf-8') as f:
#                 f.write(res)

#     def run(self):
#         # loop = asyncio.new_event_loop()
#         loop = asyncio.get_event_loop()
#         loop.run_until_complete(self.handler())
#         # loop.close()

# if __name__ == "__main__":
#     a = A()
#     a.run()