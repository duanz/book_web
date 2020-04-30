from django.contrib import admin
from task.models import Task


# Register your models here.
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'task_type', 'task_status', 'content')
