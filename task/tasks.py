
from book_web import celery_app as app
from celery import shared_task
from book_web.spiders.sheduler.novelSheduler import NovelSheduler, NovelChapterSheduler
from book_web.spiders.sheduler.novelShedulerAsync import BookInsertClient, BOOK_TYPE_DESC, BookUpdateClient, BookAutoInsertClient

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

from book_web.utils.base_logger import logger as logging
from requests.packages.urllib3.exceptions import InsecureRequestWarning
 
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@app.task(bind=True)
def handle_worker_tasks(self):
    start = time.time()
    # task()
    asyncio_task()
    stop =  time.time()
    logging.info('任务结束， 共耗时{}秒'.format(stop-start))


@shared_task
def auto_insert_books():
    logging.info('自动新增书本开始')
    start = time.time()
    BookAutoInsertClient('http://www.biquge.tv/xiaoshuodaquan/').run()
    stop =  time.time()
    logging.info('自动新增书本任务结束， 共耗时{}秒'.format(stop-start))



@shared_task
def subscribe_books_mark():
    logging.info('检查订阅书本是否可推送任务开始')
    start = time.time()
    total = 0
    subs = SubscribeBook.normal.filter(ready=False)
    if subs.chapter != subs.book.latest_chapter():
        count = Chapter.normal.filter(book=subs.book, book_type=subs.book.book_type, number__gte=subs.chapter.number).count()
        if count >= subs.chapter_num:
            total+=1
            subs.ready = True
            subs.save()

    stop =  time.time()
    logging.info('检查订阅书本是否可推送任务结束，共标记{}本, 共耗时{}秒'.format(total, stop-start))


@shared_task
def send_book_to_kindle():
    logging.info('推送订阅书本至kindle任务开始')
    start = time.time()
    total = 0
    fail = 0
    look = 0
    book_ids = SubscribeBook.normal.filter(ready=True).values('book_id').distinct()
    for book_id in book_ids:
        subs = SubscribeBook.normal.filter(ready=True, book_id=book_id)
        to_email = [sub.user.email for sub in subs]
        try:
            # 开启事务
            with transaction.atomic():
                MakeMyWord(book_id, subs[0].chapter_id, subs[0].book.latest_chapter().id)
                SendKindleEmail(book_id, list(set(to_email))).run()
                for sub in subs:
                    sub.chapter_id = subs[0].book.latest_chapter().id
                    sub.ready = False
                    sub.count = sub.count+1
                    sub.save()
        except Exception as e:
            fail += 1
            look += len(to_email)
            logging.info('推送订阅书本至kindle任务book_id：{}失败'.format(book_id))
            continue

            
    stop =  time.time()
    logging.info('推送订阅书本至kindle任务结束，共推送{}本, 失败{}本， 受影响用户{}位， 共耗时{}秒'.format(total-fail, fail, look, stop-start))



@shared_task
def auto_update_books():
    logging.info('自动更新所有书本开始')
    start = time.time()
    book_ids = SubscribeBook.normal.filter(active=True, ready=False).values('book_id')
    id_list = list(set([i['book_id'] for i in book_ids]))
    for book in id_list:
        book_id = book[0]
        s = BookUpdateClient(book_id=book_id, insert_type='with_content')
        s.run()
    stop =  time.time()
    logging.info('自动更新书本任务结束， 共耗时{}秒'.format(stop-start))



@shared_task
def cache_proxy_ip():
    logging.info("获取代理ip任务开始")
    ips = parser_utils.get_proxy_ip()
    cache.set("proxy_ips", ips)
    logging.info("获取代理ip任务结束，共找到{}条可用数据".format(len(ips)))





def asyncio_task():
    logging.info("任务开始执行！")
    queryset = Task.normal.filter(
        active=True, task_status=TASK_STATUS_DESC.WAIT)
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
                s = BookInsertClient(url=content['url'], book_type=BOOK_TYPE_DESC.Novel)
            elif task.task_type == TASK_TYPE_DESC.COMIC_INSERT:
                "漫画新增"
                s = BookInsertClient(url=content['url'], book_type=BOOK_TYPE_DESC.Comic)
            elif task.task_type in [TASK_TYPE_DESC.NOVEL_UPDATE, TASK_TYPE_DESC.COMIC_UPDATE]:
                "书本全更新"
                s = BookUpdateClient(book_id=content['book_id'])
            elif task.task_type in [TASK_TYPE_DESC.NOVEL_CHAPTER_UPDATE, TASK_TYPE_DESC.COMIC_CHAPTER_UPDATE]:
                "书本单章更新"
                s = BookUpdateClient(chapter_id=content['chapter_id'])
            elif task.task_type in [TASK_TYPE_DESC.NOVEL_MAKE_BOOK, TASK_TYPE_DESC.COMIC_MAKE_BOOK]:
                s = MakeMyWord(book_id=content['book_id'])
            elif task.task_type == TASK_TYPE_DESC.SEND_TO_KINDLE:
                s = SendKindleEmail(book_id=content['book_id'])
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
