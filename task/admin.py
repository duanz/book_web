from django.contrib import admin
from task.models import Task
from task.tasks import async_model_task

# Register your models here.


@admin.action(description="重新触发任务")
def execute_tasks_again(modeladmin, request, queryset):
    task_ids = []
    for task in queryset:
        task_ids.append(task.id)
    async_model_task(task_ids)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "task_type", "task_status", "content")
    # search_fields = ("",)
    list_filter = ("task_status", "task_type", "update_at")
    actions = [execute_tasks_again]
