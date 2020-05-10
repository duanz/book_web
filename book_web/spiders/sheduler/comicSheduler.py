import requests
from requests.utils import cookiejar_from_dict
from django.core.cache import cache
from book.models import Book, Author, Chapter, Image, ChapterImage
from book_web.utils import photo as photo_lib
from book_web.utils.base_logger import logger
from book_web.spiders.comic_parser.SimpleParser import SimpleParser
from book_web.utils.common_data import IMAGE_TYPE_DESC, BOOK_TYPE_DESC


class ComicSheduler(object):
    def __init__(self,
                 url,
                 header=None,
                 parser=SimpleParser(),
                 fetch_only=False,
                 verify_ssl=False):
        self.url = url
        self.header = header
        self.fetch_only = fetch_only
        self.verify_ssl = verify_ssl
        self.parser = parser
        self.proxy_ips = cache.get("proxy_ips")

        if hasattr(self.parser, 'request_header'):
            self.header = self.parser.request_header
        if hasattr(self.parser, 'cookie_dict'):
            self.cookies = self.parser.cookie_dict

        s = requests.Session()
        s.headers = self.header
        s.cookies = cookiejar_from_dict(self.cookies)
        if self.proxy_ips:
            s.proxies = self.proxy_ips
        self.session = s

    def run(self):
        logger.info('Using parser %s ..', type(self.parser).__name__)
        book_info, ret_data = self.get_book_info()
        chapter_list = self.get_chapter_list(ret_data)

        self.save_to_db(book_info, chapter_list)
        logger.info('comlpleted')

    def get_book_info(self):
        logger.info('get_book_info start for comic: {}'.format(self.url))
        ret_data = self.session.get(self.url)
        # logger.info('get_book_info cccc for comic: {}'.format(ret_data.text))
        book_info = self.parser.parse_info(ret_data.text)
        logger.info(
            'get_book_info comlpleted for comic, book info : {}'.format(
                book_info))
        return book_info, ret_data.text

    def get_chapter_list(self, ret_data=None):
        logger.info('get_chapter_list start for comic')
        if not ret_data:
            ret_data = self.session.get(self.url, timeout=5).text
        chapter_list = self.parser.parse_chapter(ret_data)
        logger.info('get_chapter_list comlpleted for comic: {}'.format(
            len(chapter_list)))
        return chapter_list

    def get_chapter_content(self, url):
        logger.info('get_chapter_content for comic: {} start'.format(url))
        ret_data = self.session.get(url, timeout=5).text
        image_list = self.parser.parse_image_list(ret_data)
        logger.info(
            'get_chapter_content for comic: {} comlpleted'.format(image_list))
        return image_list

    def get_chapter_content_only(self, ret_data):
        logger.info('get_chapter_content for comic: only start')
        image_list = self.parser.parse_image_list(ret_data)
        logger.info(
            'get_chapter_content for comic: {} comlpleted'.format(image_list))
        return image_list

    def _save_image_disk(self, url):
        logger.info('_save_image_disk for comic: {}'.format(url))
        resp_data = self.session.get(url, timeout=5).content
        photo_info = photo_lib.save_binary_photo(resp_data)
        return photo_info

    def _save_or_get_author_db(self, info):
        logger.info('_save_or_get_author_db for comic')
        author = Author.normal.filter(name=info['author_name']).first()
        if not author:
            author = Author()
        author.name = info['author_name']
        author.save()
        return author

    def _save_comic_db(self, info):
        logger.info('_save_comic_db')

        comic = Book.normal.filter(title=info['name'],
                                   book_type=BOOK_TYPE_DESC.Comic).first()
        if not comic:
            comic = Book()
        comic.book_type = BOOK_TYPE_DESC.Comic
        comic.title = info.get('name')
        comic.author_id = self._save_or_get_author_db(info)
        comic.desc = info.get('desc')
        comic.markeup = info.get('markeup')
        comic.title = info.get('name')
        comic.origin_addr = self.url
        comic.save()
        if isinstance(info['cover'], list):
            logger.info('_save_comic_db run loop')
            for index, url in enumerate(info['cover'], 1):
                info = self._save_image_disk(url)
                img, flag = Image.normal.get_or_create(
                    img_type=IMAGE_TYPE_DESC.COVER,
                    key=info['id'],
                    name=info['name'])
                logger.info('_save_comic_db run loop,{}==={}==={}'.format(
                    comic, info, img))
                comic.cover.add(img)

        else:
            info = self._save_image_disk(info['cover'])
            # img = Image(img_type=IMAGE_TYPE_DESC.COMIC_COVER, key=info['id'], name=info['name']).save()
            img, flag = Image.normal.get_or_create(
                img_type=IMAGE_TYPE_DESC.COVER,
                key=info['id'],
                name=info['name'])
            logger.info('_save_comic_db run singal,{}==={}==={}'.format(
                comic, info, img))
            comic.cover.add(img)
        comic.save()
        return comic

    def _save_all_chapter_db(self, comic, chapter_list):
        logger.info('_save_all_chapter_db for comic')

        for index, chapter_dict in enumerate(chapter_list, 0):
            chapter_title = list(chapter_dict.keys())[0]
            chapter_link = list(chapter_dict.values())[0]
            logger.info('{}_ -chapter-__{}'.format(chapter_title,
                                                   chapter_link))
            chapter_obj = Chapter.normal.filter(book=comic,
                                                book_type=BOOK_TYPE_DESC.Comic,
                                                title=chapter_title).first()
            if not chapter_obj:
                chapter_obj = Chapter()
            chapter_obj.comic = comic
            chapter_obj.title = chapter_title
            chapter_obj.order = index
            chapter_obj.origin_addr = chapter_link
            chapter_obj.save()

    def _update_chapter_content_db(self, comic_id):
        logger.info('_update_chapter_content_db')

        queryset = Chapter.normal.filter(book__pk=comic_id).values(
            "id", "origin_addr")

        for obj in queryset:
            count = ChapterImage.normal.filter(book__pk=comic_id,
                                               chapter=obj).count()
            if 'origin_addr' in obj and not count:
                image_list = self.get_chapter_content(obj['origin_addr'])
                for index, img in enumerate(image_list.values(), 1):
                    info = self._save_image_disk(img)
                    img, flag = Image.normal.get_or_create(
                        img_type=IMAGE_TYPE_DESC.CHAPER_CONTENT,
                        order=index,
                        key=info['id'],
                        name=info['name'])
                    ChapterImage(comic_id=comic_id,
                                 chapter_id=obj['id'],
                                 image_id=img.id,
                                 order=index).save()

    def save_to_db(self, comic_info, chapter_list):
        logger.info('save_to_db start')

        comic_obj = self._save_comic_db(comic_info)
        self._save_all_chapter_db(comic_obj, chapter_list)
        self._update_chapter_content_db(comic_obj.id)

        logger.info('save_to_db_end')


class ComicChapterSheduler(object):
    def __init__(self,
                 url,
                 comic_id,
                 chapter_id,
                 header=None,
                 parser=SimpleParser(),
                 fetch_only=False,
                 verify_ssl=False):
        self.url = url
        self.comic_id = comic_id
        self.chapter_id = chapter_id
        self.header = header
        self.fetch_only = fetch_only
        self.verify_ssl = verify_ssl
        self.parser = parser

        if 'request_header' in dir(self.parser):
            self.header = self.parser.request_header
        if hasattr(self.parser, 'cookie_dict'):
            self.cookies = self.parser.cookie_dict

        s = requests.Session()
        s.verify = False
        s.cookies = self.cookies
        s.headers = self.header

        self.session = s

    def run(self):
        logger.info('Using parser %s ..', type(self.parser).__name__)
        self.run_update_chapter()
        logger.info('comlpleted for comic')

    def get_chapter_content(self, url):
        logger.info('get_chapter_content for comic: {} start'.format(url))
        ret_data = self.session.get(url, timeout=5).text
        image_list = self.parser.parse_image_list(ret_data)
        logger.info('get_chapter_content for comic: {} comlpleted'.format(url))
        return image_list

    def _save_image_disk(self, url):
        resp_data = self.session.get(url, timeout=5).content
        photo_info = photo_lib.save_binary_photo(resp_data)
        return photo_info

    def run_update_chapter(self):
        logger.info('update_chapter_content for comic: {}'.format(self.url))

        image_list = self.get_chapter_content(self.url)
        for index, img in enumerate(image_list.values(), 1):
            info = self._save_image_disk(img)
            img, flag = Image.normal.get_or_create(
                img_type=IMAGE_TYPE_DESC.CHAPER_CONTENT,
                order=index,
                key=info['id'],
                name=info['name'])
            ChapterImage(book_id=self.comic_id,
                         chapter_id=self.chapter_id,
                         image_id=img.id,
                         order=index).save()
        Chapter.normal.filter(comic_id=self.comic_id,
                              id=self.chapter_id).update(origin_addr=self.url)
