from django_filters import rest_framework as filters
from task.models import Task


class TaskListFilter(filters.FilterSet):
    class Meta:
        model = Task
        fields = {
            'task_type': ['icontains'],
            'user': ['in'],
        }