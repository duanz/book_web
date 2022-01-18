from book.models import Book, Chapter
import book_web
from book_web.utils.base_model import BaseModel
from django.db import models
from django.contrib.auth.models import User
from book_web.utils.common_data import TASK_TYPE_DESC, TASK_STATUS_DESC, BOOK_TYPE_DESC
import json

TASK_TYPE = (
    (TASK_TYPE_DESC.BOOK_INSERT, "新增书籍"),
    (TASK_TYPE_DESC.BOOK_UPDATE, "更新书籍"),
    (TASK_TYPE_DESC.MAKE_BOOK, "制作书籍"),
    (TASK_TYPE_DESC.SEND_TO_KINDLE, "推送至Kindle"),
)

TASK_STATUS = (
    (TASK_STATUS_DESC.WAIT, "等待执行"),
    (TASK_STATUS_DESC.RUNNING, "执行中"),
    (TASK_STATUS_DESC.FINISH, "执行结束"),
    (TASK_STATUS_DESC.FAILD, "执行失败"),
)


class Task(BaseModel):
    task_type = models.CharField(
        "任务类型", default=TASK_TYPE_DESC.BOOK_INSERT, max_length=50, choices=TASK_TYPE
    )
    active = models.BooleanField("是否生效", default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="拥有者")
    task_status = models.CharField(
        "任务状态", default=TASK_STATUS_DESC.WAIT, max_length=50, choices=TASK_STATUS
    )
    content = models.CharField("任务内容", default="", max_length=300)
    result = models.CharField("任务结果", default="", max_length=300)
    progress = models.FloatField("任务进度", default=0)
    markup = models.CharField("任务备注", default="", max_length=200)

    class Meta:
        verbose_name_plural = "任务"
        db_table = "task"
        ordering = ["-update_at"]

    @staticmethod
    def create_task_for_book_insert(user_id, book_url, book_type=BOOK_TYPE_DESC.Novel):
        """创建新增书籍任务

        Args:
            user_id ([type]): [当前操作用户id]
            book_url ([type]): [书籍地址]
            book_type ([type]): [书籍类型]

        Returns:
            [Task]: [返回创建的任务]
        """
        task = Task.objects.create(
            active=True,
            user_id=user_id,
            content=json.dumps({"url": book_url, "book_type": book_type}),
        )
        return task

    @staticmethod
    def create_task_for_book_update(
        user_id,
        book_id: int = None,
        chapter_id: int = None,
        update_type="without_content",
    ):
        """创建更新书记任务

        Args:
            user_id ([int]): [操作人ID]
            book_id (int): [书籍ID，有则更新整本]. Defaults to None.
            chapter_id (int): [章节ID，有则更新此章节]. Defaults to None.
            update_type (str, optional): [更新形式，without_content,不更新内容/with_content，更新内容]. Defaults to "without_content".

        Returns:
            [Task]: [返回创建的任务]
        """
        task = Task.objects.create(
            task_type=TASK_TYPE_DESC.BOOK_UPDATE,
            active=True,
            user_id=user_id,
            content=json.dumps(
                {
                    "book_id": book_id,
                    "chapter_id": chapter_id,
                    "update_type": update_type,
                }
            ),
        )
        return task

    @staticmethod
    def create_task_for_make_book(
        user_id: int, book_id: int, start_chapter_id=None, end_chapter_id=None
    ):
        """创建打包书籍任务

        Args:
            user_id (int): [当前操作者ID]
            book_id (int): [书籍ID]
            start_id (int): [开始章节ID]
            end_id (int): [结束章节ID]

        Returns:
            [Task]: [返回创建的任务]
        """
        return Task.objects.create(
            task_type=TASK_TYPE_DESC.MAKE_BOOK,
            active=True,
            user_id=user_id,
            content=json.dumps(
                {
                    "book_id": book_id,
                    "start_chapter_id": start_chapter_id,
                    "end_chapter_id": end_chapter_id,
                }
            ),
        )

    @staticmethod
    def create_task_for_send_email(user_id: int, book_id: int, to: list):
        """创建发送书籍到邮箱任务

        Args:
            user_id (int): [当前操作者ID]
            book_id (int): [书籍ID]
            to (list): [邮件列表]

        Returns:
            [Task]: [返回创建的任务]
        """
        return Task.objects.create(
            task_type=TASK_TYPE_DESC.SEND_TO_KINDLE,
            active=True,
            user_id=user_id,
            content=json.dumps({"book_id": book_id, "to": to}),
        )
