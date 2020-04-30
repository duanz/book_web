from book.models import Chapter, Book, Author, Image, IMAGE_TYPE_DESC
from book_web.utils import photo as photo_lib
import requests

from book_web.utils.base_logger import logger
# for test
from book_web.spiders.novel_parser.BiqudaoParser import BiqudaoParser


class NovelSheduler(object):
    def __init__(self,
                 url,
                 header=None,
                 parser=BiqudaoParser(),
                 fetch_only=False,
                 verify_ssl=False):
        self.url = url
        self.header = header
        self.fetch_only = fetch_only
        self.verify_ssl = verify_ssl
        self.parser = parser

        if 'request_header' in dir(self.parser):
            self.header = self.parser.request_header

        s = requests.Session()
        self.session = s

    def run(self):
        logger.info('Using parser %s ..', type(self.parser).__name__)
        book_info = self.get_book_info()
        chapter_list = self.get_chapter_list()

        self.save_to_db(book_info, chapter_list)
        logger.info('comlpleted')

    def get_book_info(self):
        logger.info('get_book_info start')
        ret_data = self.session.get(self.url, timeout=5)
        book_info = self.parser.parse_info(ret_data)
        logger.info('get_book_info comlpleted')
        return book_info

    def get_chapter_list(self):
        logger.info('get_chapter_list start')
        ret_data = self.session.get(self.url, timeout=5)
        chapter_list = self.parser.parse_chapter(ret_data)
        logger.info('get_chapter_list comlpleted: {}'.format(chapter_list))
        return chapter_list

    def get_chapter_content(self, url):
        logger.info('get_chapter_content: {} start'.format(url))
        ret_data = self.session.get(url, timeout=5)
        content = self.parser.parse_chapter_content(ret_data)
        logger.info('get_chapter_content: {} comlpleted'.format(url))
        return content

    def _save_image(self, url, book_id):
        # count = CoverImage.normal.filter(book_id=book_id).count()
        # if count:
        #     return
        imgs = []
        if isinstance(url, list):
            for link in url:
                resp_data = self.session.get(link, timeout=5).content
                photo_info = photo_lib.save_binary_photo(resp_data)
                img = Image()
                img.key = photo_info['id']
                img.name = photo_info['name']
                img.origin_addr = url[:200]
                img.img_type = IMAGE_TYPE_DESC.COVER
                img.save()
                imgs.append(img)
        else:
            resp_data = self.session.get(url, timeout=5).content
            photo_info = photo_lib.save_binary_photo(resp_data)
            img = Image()
            img.key = photo_info['id']
            img.name = photo_info['name']
            img.origin_addr = url[:200]
            img.img_type = IMAGE_TYPE_DESC.COVER
            img.save()
            imgs.append(img)
        return imgs

    def _save_book_db(self, info):
        logger.info('_save_book_db')

        book = Book.normal.filter(title=info['name']).first()
        if not book:
            book = Book()
        book.title = info.get('name')
        book.author_id = self._save_or_get_author_db(info).id
        book.desc = info.get('desc')
        book.markeup = info.get('markeup')
        book.latest_chapter = info.get('latest_chapter')
        book.origin_addr = self.url
        book.save()
        return book

    def _save_or_get_author_db(self, info):
        author = Author.normal.filter(name=info['author_name']).first()
        if not author:
            author = Author()
        author.name = info['author_name']
        author.save()
        return author

    def _save_all_chapter_db(self, book, chapter_list):
        logger.info('_save_all_chapter_db')

        for index, chapter_dict in enumerate(chapter_list, 0):
            chapter_title = list(chapter_dict.keys())[0]
            chapter_link = list(chapter_dict.values())[0]
            logger.info('{}_ -chapter-__{}'.format(chapter_title,
                                                   chapter_link))

            chapter_obj = Chapter.normal.filter(book=book,
                                                title=chapter_title).first()
            if not chapter_obj:
                chapter_obj = Chapter()
            chapter_obj.book = book
            chapter_obj.title = chapter_title
            chapter_obj.order = index
            chapter_obj.origin_addr = chapter_link
            chapter_obj.save()

    def _update_chapter_content_db(self, book_id):
        logger.info('_update_chapter_content_db')

        queryset = Chapter.normal.filter(book__id=book_id)
        for obj in queryset:
            if obj.origin_addr and not obj.content():
                content = self.get_chapter_content(obj.origin_addr)
                obj.save_content(content)
                obj.save()

    def save_to_db(self, book_info, chapter_list):
        logger.info('save_to_db start')

        book_obj = self._save_book_db(book_info)
        cover_imgs = self._save_image(book_info['cover'], book_obj.id)
        book_obj.cover.add(*cover_imgs)
        book_obj.save()
        self._save_all_chapter_db(book_obj, chapter_list)
        self._update_chapter_content_db(book_obj.id)

        logger.info('save_to_db_end')


class NovelChapterSheduler(object):
    def __init__(self,
                 url,
                 book_id,
                 chapter_id,
                 header=None,
                 parser=BiqudaoParser(),
                 fetch_only=False,
                 verify_ssl=False):
        self.url = url
        self.book_id = book_id
        self.chapter_id = chapter_id
        self.header = header
        self.fetch_only = fetch_only
        self.verify_ssl = verify_ssl
        self.parser = parser

        if 'request_header' in dir(self.parser):
            self.header = self.parser.request_header

        s = requests.Session()
        # s.verify = False
        # s.headers = self.header

        self.session = s

    def run(self):
        logger.info('Using parser %s ..', type(self.parser).__name__)
        self.run_update_chapter()
        logger.info('comlpleted')

    def run_update_chapter(self):
        logger.info('update_chapter_content: {}'.format(self.url))
        ret_data = self.session.get(self.url, timeout=5).text
        res_data = self.parser.parse_chapter_singal(ret_data)
        chapter = Chapter.normal.get(id=self.chapter_id).update(
            origin_addr=self.url, title=res_data['title'])
        chapter.save_content(res_data['content'])
