from book_web import celery_app as app
from celery import shared_task
from book_web.spiders.sheduler.novelSheduler import NovelSheduler, NovelChapterSheduler

# from book_web.spiders.sheduler.novelShedulerAsync import BookInsertClient, BOOK_TYPE_DESC, BookUpdateClient, BookAutoInsertClient, SlowAutoInsertBookClient, FastAutoInsertBookClient
from book_web.spiders.sheduler.bookSheduler import (
    BookInsertByUrlClient,
    BOOK_TYPE_DESC,
    BookUpdateClient,
    BookInsertAllSiteClient,
)


from book_web.utils import spider_utils as parser_utils
from book_web.utils.validator import check_url
from book_web.makeBook.makeWord import MakeMyWord
from book_web.sendEmail.sendKindle import SendKindleEmail
from task.models import Task, TASK_STATUS_DESC, TASK_TYPE_DESC

from book.models import Book, SubscribeBook, Chapter

import re
import time
import requests
from django.core.cache import cache
from django.contrib.auth.models import User
from django.db import transaction
from pyquery import PyQuery as pq
from book_web.utils.common_data import BOOK_TYPE_DESC

from book_web.utils.base_logger import logger as logging
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@app.task(bind=True)
def handle_worker_tasks():
    start = time.time()
    asyncio_task()
    stop = time.time()
    logging.info("任务结束， 共耗时{}秒".format(stop - start))


@shared_task
def insert_all_books_chapters_content():
    logging.info("全站新增书本及章节任务开始")
    start = time.time()
    chapters = Chapter.objects.filter(active=False).values_list("id", flat=True)
    for chapter in chapters:
        BookUpdateClient(chapter_id=chapter, insert_type="with_content").run()
    stop = time.time()
    logging.info("全站新增书本及章节任务结束， 共耗时{}秒".format(stop - start))


@shared_task
def insert_all_books_chapters_without_content():
    logging.info("全站新增书本及章节任务开始")
    start = time.time()
    books = Book.objects.filter(is_finished=False).values_list("id", flat=True)[10:12]
    for book in books:
        BookUpdateClient(book_id=book).run()
    stop = time.time()
    logging.info("全站新增书本及章节任务结束， 共耗时{}秒".format(stop - start))


@shared_task
def insert_books_all_site_without_chapters():
    logging.info("全站新增书本任务开始")
    start = time.time()
    BookInsertAllSiteClient().run()
    stop = time.time()
    logging.info("全站新增书本任务结束， 共耗时{}秒".format(stop - start))


@shared_task
def subscribe_books_mark():
    logging.info("检查订阅书本是否可推送任务开始")
    start = time.time()
    total = 0
    subs = SubscribeBook.normal.filter(ready=False)
    for sub in subs:
        if sub.chapter != sub.book.latest_chapter():
            number = sub.chapter.number if sub.chapter else 0
            count = Chapter.normal.filter(
                book=sub.book, book_type=sub.book.book_type, number__gte=number
            ).count()
            if count >= sub.chapter_num:
                total += 1
                sub.ready = True
                sub.save()

    stop = time.time()
    logging.info("检查订阅书本是否可推送任务结束，共标记{}本, 共耗时{}秒".format(total, stop - start))


@shared_task
def send_book_to_kindle():
    logging.info("推送订阅书本至kindle任务开始")
    start = time.time()
    total = 0
    fail = 0
    look = 0
    book_ids = SubscribeBook.normal.filter(ready=True).values("book_id").distinct()
    for book_dict in book_ids:
        book_id = book_dict["book_id"]
        subs = SubscribeBook.normal.filter(ready=True, book_id=book_id)

        start_chapter, end_chapter = subs[0].chapter, subs[0].book.latest_chapter()
        # 判断需要推送的章节是否都已可用
        send_chapters = Chapter.normal.filter(
            book_id=book_id,
            number__in=[
                x
                for x in range(
                    start_chapter.number if start_chapter else 0, end_chapter.number + 1
                )
            ],
        ).values("active")
        if not all([x["active"] for x in send_chapters]):
            fail += 1
            look += 1
            logging.info("{}部分章节不可用，不予推送至kindle".format(subs[0].book.title))
            continue

        to_email = [sub.user.email for sub in subs]
        try:
            # if True:
            # 开启事务
            with transaction.atomic():
                MakeMyWord(
                    book_id, start_chapter.id if start_chapter else 0, end_chapter.id
                ).run()
                SendKindleEmail(book_id, list(set(to_email))).run()
                for sub in subs:
                    sub.chapter_id = subs[0].book.latest_chapter().id
                    sub.ready = False
                    sub.count = sub.count + 1
                    sub.save()
        except Exception as e:
            fail += 1
            look += len(to_email)
            logging.info("推送订阅书本至kindle任务book_id：{}, 失败。原因：{}".format(book_id, e))
            continue

    stop = time.time()
    logging.info(
        "推送订阅书本至kindle任务结束，共推送{}本, 失败{}本， 受影响用户{}位， 共耗时{}秒".format(
            total - fail if total > fail else 0, fail, look, stop - start
        )
    )


@shared_task
def auto_update_books():
    logging.info("自动更新订阅书本开始")
    start = time.time()
    book_ids = SubscribeBook.normal.filter(active=True).values_list(
        "book_id", flat=True
    )
    for book_id in book_ids:
        s = BookUpdateClient(book_id=book_id, insert_type="with_content", fast=True)
        s.run()
    stop = time.time()
    logging.info("自动更新书本任务结束，更新{}本， 共耗时{}秒".format(len(book_ids), stop - start))


@shared_task
def cache_proxy_ip():
    logging.info("获取代理ip任务开始")
    ips = parser_utils.get_proxy_ip(50)
    cache.set("proxy_ips", ips, 60 * 3)
    logging.info("获取代理ip任务结束，共找到{}条可用数据".format(len(ips)))


def asyncio_task():
    logging.info("任务开始执行！")
    queryset = Task.normal.filter(active=True, task_status=TASK_STATUS_DESC.WAIT)
    logging.info("获取任务列表成功：共{}条".format(queryset.count()))
    for task in queryset:
        task.task_status = TASK_STATUS_DESC.RUNNING
        task.markup = ""
        task.progress = 0
        task.save()

        try:
            # if True:
            content = eval(task.content)

            if task.task_type == TASK_TYPE_DESC.NOVEL_INSERT:
                "小说新增"
                s = BookInsertByUrlClient(
                    url=content["url"], book_type=BOOK_TYPE_DESC.Novel
                )
            elif task.task_type == TASK_TYPE_DESC.COMIC_INSERT:
                "漫画新增"
                s = BookInsertByUrlClient(
                    url=content["url"], book_type=BOOK_TYPE_DESC.Comic
                )
            elif task.task_type in [
                TASK_TYPE_DESC.NOVEL_UPDATE,
                TASK_TYPE_DESC.COMIC_UPDATE,
            ]:
                "书本全更新"
                s = BookUpdateClient(book_id=content["book_id"])
            elif task.task_type in [
                TASK_TYPE_DESC.NOVEL_CHAPTER_UPDATE,
                TASK_TYPE_DESC.COMIC_CHAPTER_UPDATE,
            ]:
                "书本单章更新"
                s = BookUpdateClient(chapter_id=content["chapter_id"])
            elif task.task_type in [
                TASK_TYPE_DESC.NOVEL_MAKE_BOOK,
                TASK_TYPE_DESC.COMIC_MAKE_BOOK,
            ]:
                s = MakeMyWord(book_id=content["book_id"])
            elif task.task_type == TASK_TYPE_DESC.SEND_TO_KINDLE:
                s = SendKindleEmail(book_id=content["book_id"])
            else:
                task.task_status = TASK_STATUS_DESC.FAILD
                task.markup = "任务未执行， {}不存在".format(task.task_type)
                task.save()
                return

            s.run()

        except Exception as e:
            error_info = "执行任务失败： {}".format(e)
            logging.info(error_info)
            task.markup = error_info
            task.task_status = TASK_STATUS_DESC.FAILD
            task.save()
            return

        task.task_status = TASK_STATUS_DESC.FINISH
        task.save()
        logging.info("执行任务结束")
        return
