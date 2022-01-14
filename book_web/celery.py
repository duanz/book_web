from __future__ import absolute_import, unicode_literals

import os
from datetime import timedelta

import django
from celery import Celery, platforms
from django.conf import settings

# 设置环境变量
# 获取当前文件夹名，即为该Django的项目名
project_name = os.path.split(os.path.abspath("."))[-1]
project_settings = "%s.settings" % project_name
os.environ.setdefault("DJANGO_SETTINGS_MODULE", project_settings)
django.setup()

app = Celery(project_name)

app.config_from_object("django.conf:settings")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
platforms.C_FORCE_ROOT = True


app.conf.update(
    CELERYBEAT_SCHEDULE={
        "schedule-cache-proxy-ip": {
            "task": "task.tasks.cache_proxy_ip",  # 获取代理ip
            # 'schedule': timedelta(hours=2)  #定时执行的间隔时间
            "schedule": timedelta(seconds=60 * 3),  # 定时执行的间隔时间
        },
        # "schedule-auto-update-books": {
        #     "task": "task.tasks.auto_update_books",  # 更新被订阅的书籍
        #     "schedule": timedelta(seconds=30)
        #     # 'schedule': crontab('0', '1,3,5,7,9,11,13,15,17,19,21,23')
        # },
        # # 'schedule-auto-insert-books': {
        # #     'task': 'task.tasks.auto_insert_books',  # 插入书籍信息
        # #     # 'schedule': timedelta(seconds=60)
        # #     'schedule': crontab('0', '1,3,5,7,9,11,13,15,17,19,21,23')
        # # },
        # "schedule-mark-subscribe-book": {
        #     "task": "task.tasks.subscribe_books_mark",  # 标记用户订阅是否符合推送条件
        #     "schedule": timedelta(seconds=180)
        #     # 'schedule': crontab('30', '1,3,5,7,9,11,13,15,17,19,21,23')
        # },
        # "schedule-send-to-kindle": {
        #     "task": "task.tasks.send_book_to_kindle",  # 推送书籍至用户kindle
        #     "schedule": timedelta(seconds=30)
        #     # 'schedule': crontab("*/30")
        # },
    }
)


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))


# app.conf.update(
#     CELERYBEAT_SCHEDULE = {
#         'handle_proxy_ips_task': {
#             'task': 'comic_web.comic_admin.tasks.get_proxy_ip_list',
#             'schedule':  datetime.timedelta(seconds=10),
#             'args': ()
#         }
#     }
# )
