from rest_framework import serializers
from rest_framework.serializers import ValidationError
from django.contrib.auth.models import User
from book_web.utils.base_logger import logger

from task.models import Task, TASK_TYPE_DESC
from task.tasks import handle_worker_tasks, auto_update_books
from book_web.utils.validator import check_url


class TaskSerializer(serializers.ModelSerializer):
    create_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S",
                                          required=False)
    update_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S",
                                          required=False)

    class Meta:
        model = Task
        fields = "__all__"

        extra_kwargs = {
            'user': {
                'read_only': True
            },
            'create_at': {
                'read_only': True
            },
            'update_at': {
                'read_only': True
            },
            'status': {
                'read_only': True
            },
        }

    def validated_content(self, value):
        try:
            content = eval(value)

            if self.get_task_type in [
                    TASK_TYPE_DESC.NOVEL_INSERT, TASK_TYPE_DESC.COMIC_INSERT
            ]:
                flag = check_url(content['url'])
            elif self.get_task_type in [
                    TASK_TYPE_DESC.NOVEL_UPDATE, TASK_TYPE_DESC.COMIC_UPDATE
            ]:
                flag = content.get('book_id', False)
            elif self.get_task_type in [
                    TASK_TYPE_DESC.NOVEL_CHAPTER_UPDATE,
                    TASK_TYPE_DESC.COMIC_CHAPTER_UPDATE
            ]:
                flag = content.get('chapter_id', False)
            elif self.get_task_type in [
                    TASK_TYPE_DESC.NOVEL_MAKE_BOOK,
                    TASK_TYPE_DESC.COMIC_MAKE_BOOK
            ]:
                flag = content.get('book_id', False)
            elif self.get_task_type == TASK_TYPE_DESC.SEND_TO_KINDLE:
                flag = content.get('book_id', False)

            if not flag:
                raise ValidationError('任务内容不合法')
            return value
        except:
            raise ValidationError('任务内容不合法')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        instance = super().create(validated_data)
        handle_worker_tasks.delay()
        return instance

    def update(self, instance, validated_data):
        validated_data['user'] = self.context['request'].user
        instance = super().update(instance, validated_data)
        handle_worker_tasks.delay()
        return instance
