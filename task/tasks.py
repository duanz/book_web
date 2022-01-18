import json
import re
import time
from typing import List, Union

import requests
from book.models import Book, Chapter, SubscribeBook

# from book_web import celery_app as app
from book_web.makeBook.makeWord import MakeMyWord
from book_web.sendEmail.sendKindle import SendKindleEmail

# from book_web.spiders.sheduler.novelShedulerAsync import BookInsertClient, BOOK_TYPE_DESC, BookUpdateClient, BookAutoInsertClient, SlowAutoInsertBookClient, FastAutoInsertBookClient
from book_web.spiders.sheduler.bookSheduler import (
    BOOK_TYPE_DESC,
    BookInsertAllSiteClient,
    BookInsertByUrlClient,
    BookUpdateClient,
)
from book_web.utils import spider_utils as parser_utils
from book_web.utils.base_logger import logger as logging
from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from tqdm import tqdm

from task.models import TASK_STATUS_DESC, TASK_TYPE_DESC, Task

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@shared_task
def handle_single_task(task_id):
    task = Task.objects.get(id=task_id)
    logging.info(f"任务{task.id}——{task.task_type}开始, 内容: {task.content}")

    start = time.time()
    task.task_status = TASK_STATUS_DESC.RUNNING
    task.markup = ""
    task.progress = 0
    task.save()

    try:
        content = json.loads(task.content)

        if task.task_type == TASK_TYPE_DESC.BOOK_INSERT:
            "书籍新增"
            s = BookInsertByUrlClient(
                url=content["url"], book_type=content["book_type"]
            )
        elif task.task_type in TASK_TYPE_DESC.BOOK_UPDATE:
            "书本全更新"
            s = BookUpdateClient(
                book_id=content["book_id"],
                chapter_id=content["chapter_id"],
                update_type=content["update_type"],
            )

        elif task.task_type in TASK_TYPE_DESC.MAKE_BOOK:
            "书籍打包"
            s = MakeMyWord(
                book_id=content["book_id"],
                start_chapter_id=content["start_chapter_id"],
                end_chapter_id=content["end_chapter_id"],
            )
        elif task.task_type == TASK_TYPE_DESC.SEND_TO_KINDLE:
            "推送"
            s = SendKindleEmail(book_id=content["book_id"], to=content["to"])
        else:
            task.task_status = TASK_STATUS_DESC.FAILD
            task.markup = "任务未执行， {}不存在".format(task.task_type)
            task.save()
            return

        s.run()

    except Exception as e:
        error_info = f"执行任务{task.id}失败: {e}"
        logging.error(error_info)
        task.markup = error_info
        task.task_status = TASK_STATUS_DESC.FAILD
        task.save()
        return

    task.task_status = TASK_STATUS_DESC.FINISH
    task.save()
    stop = time.time()
    logging.info("handle_single_task任务结束， 共耗时{}秒".format(stop - start))


@shared_task
def insert_all_books_chapters_content():
    logging.info("全站新增书本及章节任务开始")
    start = time.time()
    chapters = Chapter.objects.filter(active=False).values_list("id", flat=True)
    for chapter in chapters:
        BookUpdateClient(chapter_id=chapter, update_type="with_content").run()
    stop = time.time()
    logging.info("全站新增书本及章节任务结束， 共耗时{}秒".format(stop - start))


@shared_task
def insert_all_books_chapters_without_content():
    logging.info("全站新增书本及章节任务开始")
    start = time.time()
    books = (
        Book.objects.filter(is_finished=False)
        .order_by("update_at")
        .values_list("id", flat=True)
    )
    for book in tqdm(books, desc="更新书籍章节"):
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
    book_ids = (
        SubscribeBook.normal.filter(ready=True)
        .values_list("book_id", flat=True)
        .distinct()
    )
    user_id = 1
    for book_id in book_ids:
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
        ).values("active", flat=True)
        if not all(send_chapters):
            fail += 1
            look += 1
            logging.info("{}部分章节不可用，不予推送至kindle".format(subs[0].book.title))
            continue

        to_email = [sub.user.email for sub in subs]
        try:
            # if True:
            # 开启事务
            with transaction.atomic():
                task_makebook = Task.create_task_for_make_book(
                    user_id,
                    book_id,
                    start_chapter.id if start_chapter else 0,
                    end_chapter.id,
                )
                task_email = Task.create_task_for_send_email(
                    user_id, book_id, list(set(to_email))
                )
                model_task.delay([task_makebook.id, task_email.id])
                for sub in subs:
                    sub.chapter_id = subs[0].book.latest_chapter().id
                    sub.ready = False
                    sub.count = sub.count + 1
                    sub.save()
        except Exception as e:
            fail += 1
            look += len(to_email)
            logging.error(f"推送订阅书本至kindle任务book_id: {book_id}, 失败。原因: {e}")
            continue

    stop = time.time()
    logging.info(
        "推送订阅书本至kindle任务创建结束，共推送{}本, 失败{}本， 受影响用户{}位， 共耗时{}秒".format(
            total - fail if total > fail else 0, fail, look, stop - start
        )
    )


@shared_task
def auto_update_subscribed_books():
    logging.info("自动更新已订阅书籍开始")
    start = time.time()
    user_id = 1
    book_ids = (
        SubscribeBook.normal.filter(active=True)
        .values_list("book_id", flat=True)
        .distinct()
    )
    for book_id in book_ids:
        task = Task.create_task_for_book_update(
            user_id, book_id, update_type="with_coontent"
        )
        handle_single_task.delay(task_id=task.id)
    stop = time.time()
    logging.info("自动更新已订阅书籍任务结束，更新{}本， 共耗时{}秒".format(len(book_ids), stop - start))


@shared_task
def cache_proxy_ip():
    logging.info("获取代理ip任务开始")
    ips = parser_utils.get_proxy_ip(100)
    cache.set("proxy_ips", ips, 60 * 30)
    logging.info("获取代理ip任务结束，共找到{}条可用数据".format(len(ips)))


@shared_task
def model_task(task_id: Union[int, List]):
    """按顺序执行task模型中的任务

    Args:
        task_id (Union[int, List]): [要执行任务的ID/ID列表]
    """
    ids = [task_id] if isinstance(task_id, int) else task_id
    logging.info(f"获取任务列表成功：共{len(ids)}条")
    for tid in ids:
        handle_single_task(task_id=tid)


def async_model_task(task_id: Union[int, List]):
    """异步执行task模型中的任务

    Args:
        task_id (Union[int, List]): [要执行任务的ID/ID列表]
    """
    ids = [task_id] if isinstance(task_id, int) else task_id
    queryset = Task.normal.filter(active=True, id__in=ids)
    logging.info("获取任务列表成功：共{}条".format(queryset.count()))
    for task in queryset:
        handle_single_task.delay(task_id=task.id)
