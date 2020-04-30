from book_web.utils.base_model import BaseModel
from django.db import models
from django.contrib.auth.models import User


class TASK_TYPE_DESC:
    NOVEL_INSERT = "NOVEL_INSERT"
    NOVEL_UPDATE = "NOVEL_UPDATE"
    NOVEL_CHAPTER_UPDATE = "NOVEL_CHAPTER_UPDATE"
    COMIC_INSERT = "COMIC_INSERT"
    COMIC_UPDATE = "COMIC_UPDATE"
    COMIC_CHAPTER_UPDATE = "COMIC_CHAPTER_UPDATE"
    NOVEL_MAKE_BOOK = "NOVEL_MAKE_BOOK"
    COMIC_MAKE_BOOK = "COMIC_MAKE_BOOK"
    SEND_TO_KINDLE = "SEND_TO_KINDLE"


class TASK_STATUS_DESC:
    WAIT = "WAIT"
    RUNNING = "RUNNING"
    FINISH = "FINISH"
    FAILD = "FAILD"


TASK_TYPE = ((TASK_TYPE_DESC.NOVEL_INSERT,
              "新增小说"), (TASK_TYPE_DESC.NOVEL_UPDATE, "更新小说"),
             (TASK_TYPE_DESC.NOVEL_CHAPTER_UPDATE,
              "更新小说章节"), (TASK_TYPE_DESC.COMIC_INSERT,
                          "新增漫画"), (TASK_TYPE_DESC.COMIC_UPDATE, "更新漫画"),
             (TASK_TYPE_DESC.COMIC_CHAPTER_UPDATE,
              "更新漫画章节"), (TASK_TYPE_DESC.COMIC_MAKE_BOOK, "制作漫画BOOK"),
             (TASK_TYPE_DESC.NOVEL_MAKE_BOOK,
              "制作小说BOOK"), (TASK_TYPE_DESC.SEND_TO_KINDLE, "推送至Kindle"))

TASK_STATUS = (
    (TASK_STATUS_DESC.WAIT, "等待执行"),
    (TASK_STATUS_DESC.RUNNING, "执行中"),
    (TASK_STATUS_DESC.FINISH, "执行结束"),
    (TASK_STATUS_DESC.FAILD, "执行失败"),
)


class Task(BaseModel):
    task_type = models.CharField("任务类型",
                                 default=TASK_TYPE_DESC.NOVEL_INSERT,
                                 max_length=50,
                                 choices=TASK_TYPE)
    active = models.BooleanField("是否生效", default=False)
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             related_name='拥有者')
    task_status = models.CharField("任务状态",
                                   default=TASK_STATUS_DESC.WAIT,
                                   max_length=50,
                                   choices=TASK_STATUS)
    content = models.CharField("任务内容", default="", max_length=300)
    result = models.CharField("任务结果", default="", max_length=300)
    progress = models.FloatField("任务进度", default=0)
    markup = models.CharField("任务备注", default="", max_length=200)

    class Meta:
        verbose_name_plural = '任务'
        db_table = 'task'
        ordering = ['-update_at']
