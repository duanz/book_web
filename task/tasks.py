
from book_web import celery_app as app
from celery import shared_task
from book_web.spiders.sheduler.novelSheduler import NovelSheduler, NovelChapterSheduler
from book_web.spiders.sheduler.test_aiohttp import BookInsertClient, BOOK_TYPE_DESC, BookUpdateClient, BookAutoInsertClient
# from book_web.spiders.sheduler.novelShedulerAsync import BookInsertClient, BOOK_TYPE_DESC, BookUpdateClient

from book_web.utils import spider_utils as parser_utils
from book_web.utils.validator import check_url
from book_web.makeBook.makeWord import MakeMyWord
from book_web.sendEmail.sendKindle import SendKindleEmail
from task.models import Task, TASK_STATUS_DESC, TASK_TYPE_DESC
from book.models import Book

import re
import time
import requests
from django.core.cache import cache
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
    logging.info('推送订阅书本任务开始')
    start = time.time()
    # TODO
    '''
    遍历被订阅的book,找到对应的最新chapter
    subscribe.chapter==chapter?'':ready=True
    '''
    stop =  time.time()
    logging.info('推送订阅书本任务结束， 共耗时{}秒'.format(stop-start))



@shared_task
def auto_update_books():
    logging.info('自动更新书本开始')
    start = time.time()
    query_set = Book.normal.filter(on_shelf=True).values_list('id')

    for book in query_set:
        book_id = book[0]
        s = BookUpdateClient(book_id=book_id, insert_type='with_content')
        s.run()
    stop =  time.time()
    logging.info('自动更新书本任务结束， 共耗时{}秒'.format(stop-start))



@shared_task
def cache_proxy_ip():
    """定时任务：缓存代理IP任务"""

    logging.info("get proxy ip list start ")
    url = "http://127.0.0.1:5010/get"
    res = []
    try:
        for i in range(10):
            res.append(requests.get(url, timeout=3).json())
    except:
        return []
    if not res:
        return
    
    ips = []
    for info in res:
        ips.append('http://{}'.format(info['proxy']))

    ok_ips = available_ip(set(ips))
    ok_ips = set((ips))
    # 存储到缓存
    # cache.delete('proxy_ips')
    cache.set("proxy_ips", list(ok_ips))
    logging.info("set proxy ip list to cache finished")
    return cache.get('proxy_ips')


def available_ip(ip_list):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 \
        (KHTML, like Gecko) Chrome/65.0.3325.146 Safari/537.36',
        }
    sesseion = requests.session()
    ips = []
    for ip in ip_list:
        try:
            response = sesseion.get('https://www.baidu.com', headers=headers,
                            proxies={'http': ip}, verify=False, timeout=3)
            # logging.info('检查代理IP%s: %s'% (ip, response.status_code))
            if response.status_code==200:
                ips.append(ip)
        except TimeoutError:
            continue
    return ips





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


        # try:
        if True:
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
            
        # except Exception as e:
        #     error_info = "执行任务失败： {}".format(e)
        #     logging.info(error_info)
        #     task.markup = error_info
        #     task.task_status = TASK_STATUS_DESC.FAILD
        #     task.save()
        #     return

        task.task_status = TASK_STATUS_DESC.FINISH
        task.save()
        logging.info("执行任务结束")
        return
